import csv
import json
from datetime import date
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail.message import EmailMessage
from django.db import IntegrityError, transaction
from django.db.models import Q

from django.utils.encoding import force_text

import requests
from celery.utils.log import get_task_logger
from dateutil.relativedelta import relativedelta

from etools.applications.users.models import Country, UserProfile
from etools.applications.vision.exceptions import VisionException
from etools.applications.vision.models import VisionSyncLog
from etools.applications.vision.vision_data_synchronizer import VISION_NO_DATA_MESSAGE
from etools.config.celery import app

logger = get_task_logger(__name__)


class UserMapper(object):

    KEY_ATTRIBUTE = 'internetaddress'

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

    USER_ATTR_MAP = {
        'dn': 'dn',
        'username': 'mail',
        'email': 'internetaddress',
        'first_name': 'givenName',
        'last_name': 'sn',
    }

    PROFILE_ATTR_MAP = {
        'phone_number': 'telephoneNumber',
        'country': 'unicefBusinessAreaCode',
        'staff_id': 'unicefIndexNumber',
        'section_code': 'unicefSectionCode',
        'post_title': 'functionalTitle'
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
                    logger.info(u"Country Updated for {}".format(obj))
                    return True

        return False

    def _set_attribute(self, obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """

        field = obj._meta.get_field(attr)
        if type(value) == list:
            value = u'- '.join([str(val) for val in value])
        if field.get_internal_type() == "CharField" and value and len(value) > field.max_length:
            cleaned_value = value[:field.max_length]
            logger.warn(u'The attribute "%s" was trimmed from "%s" to "%s"' % (attr, value, cleaned_value))
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
    def create_or_update_user(self, record):

        if not self.record_is_valid(record):
            return

        key_value = record[self.KEY_ATTRIBUTE]
        logger.debug(key_value)

        try:
            user, created = get_user_model().objects.get_or_create(
                email=key_value, username=key_value)

            if created:
                user.set_unusable_password()
                user.groups.add(self.groups['UNICEF User'])
                logger.info(u'Group added to user {}'.format(user))

            try:
                profile = user.profile
            except ObjectDoesNotExist:
                logger.warning(u'No profile for user {}'.format(user))
                return

            self.update_user(user, record)
            self.update_profile(profile, record)

        except IntegrityError as e:
            logger.exception(u'Integrity error on user retrieving: {} - exception {}'.format(key_value, e))

    def _set_supervisor(self, profile, manager_id):
        if not manager_id or manager_id == 'Vacant':
            return False
        if profile.supervisor and profile.supervisor.profile.staff_id == manager_id:
            return False

        try:
            supervisor = self.section_users.get(
                manager_id,
                get_user_model().objects.get(
                    is_active=True,
                    profile__staff_id=manager_id
                )
            )
            self.section_users[manager_id] = supervisor
        except get_user_model().DoesNotExist:
            logger.warning(u"this user does not exist in the db to set as supervisor: {}".format(manager_id))
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
            synchronizer = UserVisionSynchronizer('GetOrgChartUnitsInfo_JSON', code)
            logger.info(u"Mapping for section {}".format(code))
            for in_user in synchronizer.response:
                # if the user has no staff id don't bother for supervisor
                if not in_user.get('STAFF_ID'):
                    continue
                # get user:
                try:
                    user = self.section_users.get(
                        in_user['STAFF_ID'],
                        get_user_model().objects.get(profile__staff_id=in_user['STAFF_ID'])
                    )
                    self.section_users[in_user['STAFF_ID']] = user
                except get_user_model().DoesNotExist:
                    logger.warning(u"this user does not exist in the db: {}".format(in_user['STAFF_EMAIL']))
                    continue

                profile_updated = self._set_attribute(user.profile, "post_number", in_user["STAFF_POST_NO"])
                profile_updated = self._set_attribute(
                    user.profile, "vendor_number", in_user["VENDOR_CODE"]) or profile_updated

                supervisor_updated = self._set_supervisor(user.profile, in_user["MANAGER_ID"])

                if profile_updated or supervisor_updated:
                    logger.info(u"saving profile for {}, supervisor updated: {}, profile updated: {}".format(
                        user, supervisor_updated, profile_updated))
                    user.profile.save()

    def record_is_valid(self, record):
        if self.KEY_ATTRIBUTE not in record:
            logger.info(u"Discarding Record {} field is missing".format(self.KEY_ATTRIBUTE))
            return False
        for field in self.REQUIRED_USER_FIELDS:
            if isinstance(field, str):
                if not record.get(field, False):
                    logger.info(u"User doesn't have the required fields {} missing".format(field))
                    return False
            elif isinstance(field, tuple):
                allowed_values = field[1]
                if isinstance(allowed_values, str):
                    allowed_values = [allowed_values, ]

                if record.get(field[0], False) not in allowed_values:
                    logger.debug(u"User is not in Unicef organization {}".format(field[1]))
                    return False
        return True

    def update_user(self, user, record):
        modified = False
        for attr, record_attr in self.USER_ATTR_MAP.items():

            record_value = record.get(record_attr, None)
            if record_value:
                attr_modified = self._set_attribute(user, attr, record_value)
                modified = modified or attr_modified

        if modified:
            logger.debug(f'Updated User: {user}')
            user.save()

    def update_profile(self, profile, record):
        modified = False
        for attr, record_attr in self.PROFILE_ATTR_MAP.items():
            record_value = record.get(record_attr, None)
            if record_value:
                attr_modified = self._set_attribute(profile, attr, record_value)
                modified = modified or attr_modified

        if modified:
            logger.debug(f'Updated Profile: {profile.user}')
            profile.save()


class AzureUserMapper(UserMapper):
    KEY_ATTRIBUTE = 'userPrincipalName'

    REQUIRED_USER_FIELDS = [
        'givenName',
        'userPrincipalName',
        'mail',
        'surname',
        'userType',
        ('companyName', ['UNICEF', ]),
    ]

    USER_ATTR_MAP = {
        'username': 'userPrincipalName',
        'email': 'userPrincipalName',
        'first_name': 'givenName',
        'last_name': 'surname',
    }

    PROFILE_ATTR_MAP = {
        'guid': 'id',
        'phone_number': 'businessPhones',
        'country': 'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute1',
        'staff_id': 'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute2',
        'post_title': 'jobTitle'
    }


def sync_users_remote():
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    user_sync = UserMapper()
    with storage.open('saml/etools.dat') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=bytes('|'))
        for row in reader:
            uni_row = {
                str(key, 'latin-1'): str(value, 'latin-1') for key, value in row.items()}
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
        log.exception_message = force_text(e)
        raise VisionException(*e.args)
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
        log.exception_message = force_text(e)
        raise VisionException(*e.args)
    finally:
        log.save()


class UserVisionSynchronizer(object):

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
        return '{}' if data == VISION_NO_DATA_MESSAGE else data

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.required_keys:
                if key not in record:
                    return False
                if key == "STAFF_EMAIL" and not record[key]:
                    return False
            return True

        return [rec for rec in records if is_valid_record(rec)]

    def _load_records(self):
        logger.debug(self.url)
        response = requests.get(
            self.url,
            headers={'Content-Type': 'application/json'},
            auth=(settings.VISION_USER, settings.VISION_PASSWORD),
            verify=False
        )
        if response.status_code != 200:
            raise VisionException('Load data failed! Http code: {}'.format(response.status_code))

        return self._get_json(response.json())

    def _convert_records(self, records):
        return json.loads(records)

    @property
    def response(self):
        return self._filter_records(self._convert_records(self._load_records()))


@app.task
def user_report():

    today = date.today()
    start_date = today + relativedelta(months=-1)

    qs = Country.objects.exclude(schema_name__in=['public', 'uat', 'frg'])
    fieldnames = ['country', 'total_users', 'unicef_users', 'users_last_month', 'unicef_users_last_month']
    csvfile = StringIO()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for country in qs:
        writer.writerow({
            'country': country,
            'total_users': get_user_model().objects.filter(profile__country=country).count(),
            'unicef_users': get_user_model().objects.filter(
                profile__country=country,
                email__endswith='@unicef.org'
            ).count(),
            'users_last_month': get_user_model().objects.filter(
                profile__country=country,
                last_login__gte=start_date
            ).count(),
            'unicef_users_last_month': get_user_model().objects.filter(
                profile__country=country,
                email__endswith='@unicef.org',
                last_login__gte=start_date
            ).count(),
        })
    mail = EmailMessage('Report Latest Users', 'Report generated', 'etools-reports@unicef.org', settings.REPORT_EMAILS)
    mail.attach('users.csv', csvfile.getvalue().encode('utf-8'), 'text/csv')
    mail.send()
