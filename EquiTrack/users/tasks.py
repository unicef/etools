import csv
import json
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Q

import requests

from EquiTrack.celery import app
from users.models import Country, Section, User, UserProfile
from vision.models import VisionSyncLog
from vision.vision_data_synchronizer import VisionException

logger = logging.getLogger()


class UserMapper(object):

    SPECIAL_FIELDS = ['country']
    REQUIRED_USER_FIELDS = [
        'givenName',
        'internetaddress',
        'mail',
        'sn'
    ]
    USER_FIELDS = [
        'dn',
        'upn',
        'displayName',
        'functionalTitle',
        'gender',
        'email',
        'givenName',
        'sn',
        'unicefBusinessAreaCode',
        'unicefSectionCode'
    ]
    ATTR_MAP = {
        'dn': 'dn',
        'mail': 'username',
        'internetaddress': 'email',
        'givenName': 'first_name',
        'sn': 'last_name',
        'telephoneNumber': 'phone_number',
        'unicefBusinessAreaCode': 'country',
        'unicefIndexNumber': 'staff_id',
        'unicefSectionCode': 'section_code',
        'functionalTitle': 'post_title'
    }

    def __init__(self):
        self.countries = {}
        self.sections = {}
        self.groups = {}
        self.section_users = {}
        self.groups['UNICEF User'] = Group.objects.get(name='UNICEF User')

    def _get_country(self, business_area_code):
        if not self.countries.get('UAT', None):
            self.countries['UAT'] = Country.objects.get(name='UAT')
        if business_area_code not in self.countries:
            self.countries[business_area_code] = Country.objects.filter(business_area_code=business_area_code).first()
        return self.countries[business_area_code] or self.countries['UAT']

    def _get_section(self, section_name, section_code):
        if not self.sections[section_name]:
            self.sections[section_name] = Section.objects.get_or_create(name=section_name, code=section_code)
        return self.sections[section_name]

    def _set_simple_attr(self, obj, attr, cleaned_value):
        old_value = getattr(obj, attr)
        if cleaned_value != old_value:
            setattr(obj, attr, cleaned_value)
            return True

        return False

    def _set_special_attr(self, obj, attr, cleaned_value):

        if attr == 'country':
            # ONLY SYNC WORKSPACE IF IT HASN'T BEEN SET ALREADY
            if not obj.country_override:
                # cleaned value is actually business area code -> see mapper
                new_country = self._get_country(cleaned_value)
                if not obj.country == new_country:
                    obj.country = self._get_country(cleaned_value)
                    obj.countries_available.add(obj.country)
                    logger.info("Country Updated for {}".format(obj))
                    return True

        return False

    def _set_attribute(self, obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """
        # clean the value
        field = obj._meta.get_field(attr)
        if field.get_internal_type() == "CharField" and len(value) > field.max_length:
            cleaned_value = value[:field.max_length]
            logging.warn('The attribute "%s" was trimmed from "%s" to "%s"' %
                         (attr, value, cleaned_value))
        else:
            cleaned_value = value
        if cleaned_value == '':
            cleaned_value = None

        # if section code.. only take last 4 digits
        if cleaned_value and attr == 'section_code':
            cleaned_value = cleaned_value[-4:]

        if attr in self.SPECIAL_FIELDS:
            return self._set_special_attr(obj, attr, cleaned_value)

        return self._set_simple_attr(obj, attr, cleaned_value)

    @transaction.atomic
    def create_or_update_user(self, ad_user):
        logger.debug(ad_user['sn'], ad_user['givenName'])
        for field in self.REQUIRED_USER_FIELDS:
            if not ad_user[field]:
                logger.info("User doesn't have the required fields {}".format(ad_user))
                return

        # TODO: MODIFY THIS TO USER THE GUID ON THE PROFILE INSTEAD OF EMAIL on the USer
        user, created = User.objects.get_or_create(email=ad_user['internetaddress'],
                                                   username=ad_user['internetaddress'][:30])
        if created:
            user.set_unusable_password()

        try:
            profile = user.profile
        except ObjectDoesNotExist:
            logger.warning('No profile for user {}'.format(user))
            return

        profile_modified = False
        # TODO: user.is_staff should not be set for regular UNICEF users.. global refactor needed
        user_modified = False if user.is_staff and user.is_active else True
        # TODO: in the future see if ADFS returns somewhere whether users are active or not.
        user.is_staff = user.is_staff or True
        user.is_active = user.is_active or True

        if created:
            user.groups.add(self.groups['UNICEF User'])
            logger.info('Group added to user {}'.format(user))

        # most attributes are direct maps.
        for attr, attr_val in ad_user.iteritems():

            if hasattr(user, self.ATTR_MAP.get(attr, 'unusable_attr')):
                u_modified = self._set_attribute(
                    user, self.ATTR_MAP.get(attr, 'unusable_attr'), ad_user[attr]
                )
                user_modified = user_modified or u_modified

            if self.ATTR_MAP.get(attr, 'unusable_attr') not in ['email', 'first_name', 'last_name', 'username'] \
                    and hasattr(profile, self.ATTR_MAP.get(attr, 'unusable_attr')):
                modified = self._set_attribute(
                    profile, self.ATTR_MAP.get(attr, 'unusable_attr'), ad_user[attr]
                )
                profile_modified = profile_modified or modified
        try:
            if user_modified:
                logger.debug('saving modified user')
                user.save()
            if profile_modified:
                logger.debug('saving profile for: {}'.format(user))
                profile.save()
        except IntegrityError as e:
            logging.error('Integrity error on user: {} - exception {}'.format(user.email, e))

    def _set_supervisor(self, profile, manager_id):
        if not manager_id or manager_id == 'Vacant':
            return False
        if profile.supervisor and profile.supervisor.profile.staff_id == manager_id:
            return False

        try:
            supervisor = self.section_users.get(manager_id, User.objects.get(profile__staff_id=manager_id))
            self.section_users[manager_id] = supervisor
        except User.DoesNotExist:
            logger.warning("this user does not exist in the db to set as supervisor: {}".format(manager_id))
            return False

        profile.supervisor = supervisor
        return True

    def map_users(self):

        # get all section codes
        section_codes = UserProfile.objects.values_list('section_code', flat=True)\
            .exclude(Q(section_code__isnull=True) | Q(section_code=''))\
            .distinct()

        for code in section_codes:
            self.section_users = {}
            synchronizer = UserSynchronizer('GetOrgChartUnitsInfo_JSON', code)
            logger.info("Mapping for section {}".format(code))
            for in_user in synchronizer.response:
                # if the user has no staff id don't bother for supervisor
                if not in_user.get('STAFF_ID'):
                    continue
                # get user:
                try:
                    user = self.section_users.get(
                        in_user['STAFF_ID'],
                        User.objects.get(profile__staff_id=in_user['STAFF_ID'])
                    )
                    self.section_users[in_user['STAFF_ID']] = user
                except User.DoesNotExist:
                    logger.warning("this user does not exist in the db: {}".format(in_user['STAFF_EMAIL']))
                    continue

                profile_updated = self._set_attribute(user.profile, "post_number", in_user["STAFF_POST_NO"])
                profile_updated = self._set_attribute(
                    user.profile, "vendor_number", in_user["VENDOR_CODE"]) or profile_updated

                supervisor_updated = self._set_supervisor(user.profile, in_user["MANAGER_ID"])

                if profile_updated or supervisor_updated:
                    logger.info("saving profile for {}, supervisor updated: {}, profile updated: {}".format(
                        user, supervisor_updated, profile_updated))
                    user.profile.save()


def sync_users_remote():
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    user_sync = UserMapper()
    with storage.open('saml/etools.dat') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        for row in reader:
            uni_row = {unicode(key, 'latin-1'): unicode(value, 'latin-1') for key, value in row.iteritems()}
            user_sync.create_or_update_user(uni_row)


@app.task
def sync_users():
    log = VisionSyncLog(
        country=Country.objects.get(schema_name="public"),
        handler_name='UserADSync'
    )
    try:
        sync_users_remote()
    except Exception as e:
        log.exception_message = e.message
        raise VisionException(message=e.message)
    finally:
        log.save()


@app.task
def map_users():
    log = VisionSyncLog(
        country=Country.objects.get(schema_name="public"),
        handler_name='UserSupervisorMapper'
    )
    try:
        user_sync = UserMapper()
        user_sync.map_users()
    except Exception as e:
        log.exception_message = e.message
        raise VisionException(message=e.message)
    finally:
        log.save()


def sync_users_local(n=20):
    user_sync = UserMapper()
    with open('/code/etools.dat') as csvfile:
        # with open('/Users/Rob/Downloads/users.dat') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        i = 0
        for row in reader:
            i += 1
            if i == n:
                break
            uni_row = {unicode(key, 'latin-1'): unicode(value, 'latin-1') for key, value in row.iteritems()}
            user_sync.create_or_update_user(uni_row)


class UserSynchronizer(object):

    NO_DATA_MESSAGE = u'No Data Available'
    REQUIRED_KEYS_MAP = {
        'GetOrgChartUnitsInfo_JSON': (
            "ORG_UNIT_NAME",  # VARCHAR2	Vendor Name
            "STAFF_ID",  # VARCHAR2    Staff Id
            "MANAGER_ID",  # VARCHAR2    Manager Id
            "ORG_UNIT_CODE",  # VARCHAR2    Org Unit Code
            "VENDOR_CODE",  # VARCHAR2    Vendor code
            "STAFF_EMAIL"
        )
    }

    def __init__(self, endpoint_name, parameter):
        self.url = '{}/{}/{}'.format(
            settings.VISION_URL,
            endpoint_name,
            parameter
        )
        self.required_keys = self.REQUIRED_KEYS_MAP[endpoint_name]

    def _get_json(self, data):
        return '{}' if data == self.NO_DATA_MESSAGE else data

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.required_keys:
                if key not in record:
                    return False
                if key == "STAFF_EMAIL" and not record[key]:
                    return False
            return True

        return filter(is_valid_record, records)

    def _load_records(self):
        logger.debug(self.url)
        response = requests.get(
            self.url,
            headers={'Content-Type': 'application/json'},
            auth=(settings.VISION_USER, settings.VISION_PASSWORD),
            verify=False
        )
        if response.status_code != 200:
            raise VisionException(
                message=('Load data failed! Http code: {}'.format(response.status_code))
            )

        return self._get_json(response.json())

    def _convert_records(self, records):
        return json.loads(records)

    @property
    def response(self):
        return self._filter_records(self._convert_records(self._load_records()))
