from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction

from celery.utils.log import get_task_logger

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, Realm, UserProfile

logger = get_task_logger(__name__)


class AzureUserMapper:

    KEY_ATTRIBUTE = 'userPrincipalName'
    SPECIAL_FIELDS = ['country']

    REQUIRED_USER_FIELDS = [
        'givenName',
        'userPrincipalName',
        'mail',
        'surname',
        'userType',
        # ('companyName', ['UNICEF', ]),
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

    def __init__(self):
        self.countries = {}
        self.groups = {}
        self.groups['UNICEF User'] = Group.objects.get(name='UNICEF User')
        self.unicef_organization = Organization.objects.get(name='UNICEF')

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
                    Realm.objects.get_or_create(
                        user=obj.user,
                        country=obj.country,
                        organization=self.unicef_organization,
                        group=self.groups['UNICEF User'])
                    # TODO: discuss : reset permission when changing country ?
                    logger.info("Country Updated for {}".format(obj))
                    return True

        return False

    def _set_attribute(self, obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """

        field = obj._meta.get_field(attr)
        if type(value) == list:
            value = '- '.join([str(val) for val in value])
        if field.get_internal_type() == "CharField" and value and len(value) > field.max_length:
            cleaned_value = value[:field.max_length]
            logger.warn('The attribute "%s" was trimmed from "%s" to "%s"' % (attr, value, cleaned_value))
        else:
            cleaned_value = value
        if cleaned_value == '':
            cleaned_value = None

        if attr in self.SPECIAL_FIELDS:
            return self._set_special_attr(obj, attr, cleaned_value)

        return self._set_simple_attr(obj, attr, cleaned_value)

    @transaction.atomic
    def create_or_update_user(self, record):
        status = {'processed': 1, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        if not self.record_is_valid(record):
            status['skipped'] = 1
            return status

        key_value = record[self.KEY_ATTRIBUTE].lower()
        logger.debug(key_value)

        try:
            user, created = get_user_model().objects.get_or_create(
                email=key_value, username=key_value, defaults={'is_staff': True})

            if created:
                status['created'] = int(created)
                user.set_unusable_password()
                # TODO: TBD about UAT
                Realm.objects.create(
                    user=user,
                    country=self._get_country('UAT'),
                    organization=self.unicef_organization,
                    group=self.groups['UNICEF User'])
                logger.info('Group added to user {}'.format(user))

            profile, _ = UserProfile.objects.get_or_create(user=user)
            user_updated = self.update_user(user, record)
            profile_updated = self.update_profile(profile, record)

            if not created and (user_updated or profile_updated):
                status['updated'] = 1

        except IntegrityError as e:
            logger.exception('Integrity error on user retrieving: {} - exception {}'.format(key_value, e))
            status['created'] = status['updated'] = 0
            status['errors'] = 1

        return status

    def record_is_valid(self, record):
        if self.KEY_ATTRIBUTE not in record:
            logger.info("Discarding Record {} field is missing".format(self.KEY_ATTRIBUTE))
            return False
        for field in self.REQUIRED_USER_FIELDS:
            if isinstance(field, str):
                if not record.get(field, False):
                    logger.info("User doesn't have the required fields {} missing".format(field))
                    return False
            elif isinstance(field, tuple):
                allowed_values = field[1]
                if isinstance(allowed_values, str):
                    allowed_values = [allowed_values, ]

                if record.get(field[0], False) not in allowed_values:
                    logger.debug("User is not in UNICEF organization {}".format(field[1]))
                    return False
        return True

    def update_user(self, user, record):
        modified = False
        for attr, record_attr in self.USER_ATTR_MAP.items():
            record_value = record.get(record_attr, None)
            if record_value:
                if attr in ["username", "email"]:
                    record_value = record_value.lower()
                attr_modified = self._set_attribute(user, attr, record_value)
                modified = modified or attr_modified

        if modified:
            logger.debug(f'Updated User: {user}')
            user.save()

        return modified

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

        return modified
