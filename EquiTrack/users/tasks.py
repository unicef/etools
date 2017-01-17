import csv
import json
import logging
from django.conf import settings

import requests
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from .models import User, UserProfile, Country, Section
from django.contrib.auth.models import Group

from vision.vision_data_synchronizer import VisionException
try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError:
    class SiteProfileNotAvailable(Exception):
        pass

special_fields = ['country', 'unicefSectionCode', 'unicefSectionName']

user_fields = [
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

attr_map = {
    'dn': 'dn',
    'mail': 'username',
    'internetaddress': 'email',
    'givenName': 'first_name',
    'sn': 'last_name',
    'telephoneNumber': 'phone_number',
    'unicefBusinessAreaCode': 'country',
    'unicefpernr': 'staff_id',
    'unicefSectionCode' : 'section_code'

}

countries = {}
sections = {}
groups = {}

def _get_country(business_area_code):
    if not countries.get('UAT', None):
        countries['UAT'] = Country.objects.get(name='UAT')
    if business_area_code not in countries:
        countries[business_area_code] = Country.objects.filter(business_area_code=business_area_code).first()
    return countries[business_area_code] or countries['UAT']


def _get_section(section_name, section_code):
    if not sections[section_name]:
        sections[section_name] = Section.objects.get_or_create(name=section_name, code=section_code)
    return sections[section_name]

def _set_special_attr(obj, attr, cleaned_value):

    if attr == 'country':
        if not obj.country:
            obj.country = _get_country(cleaned_value)
            obj.countries_available.add(obj.country)
            return True

    return False


def _set_simple_attr(obj, attr, cleaned_value):
    old_value = getattr(obj, attr)
    if cleaned_value != old_value:
        setattr(obj, attr, cleaned_value)
        return True

    return False


def _set_attribute(obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """
        # clean the value
        field = obj._meta.get_field_by_name(attr)
        if len(value) > field[0].max_length:
            cleaned_value = value[:field[0].max_length]
            logging.warn('The attribute "%s" was trimmed from "%s" to "%s"' %
                        (attr, value, cleaned_value))
        else:
            cleaned_value = value
        if cleaned_value == '':
            cleaned_value = None

        # if section code.. only take last 4 digits
        if cleaned_value and attr == 'section_code':
            cleaned_value = cleaned_value[-4:]

        if attr in special_fields:
            return _set_special_attr(obj, attr, cleaned_value)

        return _set_simple_attr(obj, attr, cleaned_value)


@transaction.atomic
def create_or_update_user(ad_user):
    print(ad_user['sn'], ad_user['givenName'])
    #TODO: MODIFY THIS TO USER THE GUID ON THE PROFILE INSTEAD OF EMAIL on the USer
    user, created = User.objects.get_or_create(email=ad_user['internetaddress'], username=ad_user['internetaddress'])
    user.set_unusable_password()
    try:
        profile = user.profile
    except ObjectDoesNotExist:
        print 'No profile for user {}'.format(user)
        return
    except SiteProfileNotAvailable:
        print 'No profile for user SPNA {}'.format(user)
        return

    profile_modified = False
    user_modified = False if user.is_staff and user.is_active else True
    user.is_staff = user.is_staff or True
    user.is_active = user.is_staff or True

    if created:
        user.groups.add(groups['UNICEF User'])
        print 'Group added to user {}'.format(user)

    # most attributes are direct maps.
    for attr, attr_val in ad_user.iteritems():

        if hasattr(user, attr_map.get(attr, 'unusable_attr')):
            u_modified = _set_attribute(
                user, attr_map.get(attr, 'unusable_attr'), ad_user[attr]
            )
            user_modified = user_modified or u_modified

        if attr_map.get(attr, 'unusable_attr') not in ['email', 'first_name', 'last_name', 'username'] \
                and hasattr(profile, attr_map.get(attr, 'unusable_attr')):

            modified = _set_attribute(
                profile, attr_map.get(attr, 'unusable_attr'), ad_user[attr]
            )
            profile_modified = profile_modified or modified

    # # section requires special attention:
    # section_code = ad_user.get('unicefSectionCode', None)
    # section_name = ad_user.get('unicefSectionName', None)
    #
    # if section_name and section_code:
    #     modified = _set_attribute(profile, 'section', _get_section(section_name, section_code))
    #     profile_modified = profile_modified or modified

    if user_modified:
        print 'saving modified user'
        user.save()
    if profile_modified:
        print 'saving profile for: {} {}'.format(user, user.profile)
        profile.save()

def map_users():
    # get the users from IM (bania's file)
        # map sections and staff_ids and all other relevant fields

    # get all section codes
    section_codes = UserProfile.objects.values_list('section_code', flat=True)\
            .exclude(section_code__isnull=True)\
            .distinct()

    for code in section_codes:
        synchronizer = UserSynchronizer('GetOrgChartUnitsInfo_JSON', code)
        print "Mapping for section {}".format(code)
        for in_user in synchronizer.response:
            # get user:
            try:
                user = User.objects.get(profile__staff_id=in_user['STAFF_ID'])
            except User.DoesNotExist:
                print "this user does not exist in the db: {}".format(in_user['STAFF_EMAIL'])
                continue

            profile_updated = _set_attribute(user.profile, "post_number", in_user["STAFF_POST_NO"])
            if profile_updated:
                print "saving profile for {}".format(user)
                user.profile.save()
    # for each section call the "GetOrgChartUnitsInfo" to get all section org units
        # for each OrgChart get User by staff_id
            # set vendor code on user if vendor code changed
            # set staff post number and title if changed
            # if not set telephone number set
            # query the Users on staff_id -> manager_id and set supervisor to the user

    pass


def sync_users():
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    with storage.open('saml/etools.dat') as csvfile:
    #with open('/Users/Rob/Downloads/users.dat') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        i = 0
        for row in reader:
            i += 1
            # print(row['sn'], row['givenName'])
            if i == 10:
                break
            create_or_update_user(row)

def sync_users_local():
    groups['UNICEF User'] = Group.objects.get(name='UNICEF User')
    with open('/code/etools.dat') as csvfile:
    #with open('/Users/Rob/Downloads/users.dat') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        i = 0
        for row in reader:
            i += 1
            # print(row['sn'], row['givenName'])
            if i == 20:
                break
            create_or_update_user(row)

class UserSynchronizer(object):


    NO_DATA_MESSAGE = u'No Data Available'
    REQUIRED_KEYS_MAP = {
        'GetOrgChartUnitsInfo_JSON': (
            "ORG_UNIT_NAME",  # VARCHAR2	Vendor Name
            "STAFF_ID",  # VARCHAR2    Staff Id
            "MANAGER_ID",  # VARCHAR2    Manager Id
            "ORG_UNIT_CODE",  # VARCHAR2    Org Unit Code
            "VENDOR_CODE",  # VARCHAR2    Vendor code
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
        return [] if data == self.NO_DATA_MESSAGE else data

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.required_keys:
                if key not in record:
                    return False
            return True

        return filter(is_valid_record, records)

    def _load_records(self):
        print self.url
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