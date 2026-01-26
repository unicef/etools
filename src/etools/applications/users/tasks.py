import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone

from celery.utils.log import get_task_logger
from requests import HTTPError

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.last_mile.services.permissions_service import LMSMPermissionsService
from etools.applications.organizations.models import Organization
from etools.applications.partners.prp_api import PRPAPI
from etools.applications.partners.serializers.prp_v1 import PRPSyncUserSerializer
from etools.applications.users.mixins import PARTNER_ACTIVE_GROUPS
from etools.applications.users.models import Country, Realm, User, UserProfile
from etools.config.celery import app

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
                    obj.organization = self.unicef_organization
                    Realm.objects.get_or_create(
                        user=obj.user,
                        country=new_country,
                        organization=self.unicef_organization,
                        group=self.groups['UNICEF User'])
                    logger.info('UNICEF User Group added to user {}'.format(obj.user))

                    # deactivate realms from previous user country
                    # commenting out to support stretch assignments
                    # Realm.objects.filter(
                    #     user=obj.user,
                    #     country=obj.country,
                    #     organization=self.unicef_organization).update(is_active=False)

                    obj.country = self._get_country(cleaned_value)
                    logger.info("Country Updated for {}".format(obj))
                    return True

        return False

    def _set_attribute(self, obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """

        field = obj._meta.get_field(attr)
        if isinstance(value, list):
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

                user.profile.organization = self.unicef_organization
                user.profile.save(update_fields=['organization'])

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
            logger.info(f'User {user} updated with {record}')
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


@app.task
def notify_user_on_realm_update(user_pk):
    user = User.objects.get(pk=user_pk)
    active_realms = user.realms\
        .filter(country=connection.tenant, is_active=True)\
        .values('country__name', 'organization__name', 'group__name')
    if active_realms:
        email_context = {
            'user_full_name': user.get_full_name(),
            'active_realms': list(active_realms),
        }
        recipients = [user.email]

        send_notification_with_template(
            recipients=recipients,
            template_name='users/amp/role-update',
            context=email_context
        )


@app.task
def sync_realms_to_prp(user_pk, last_modified_at_timestamp, retry_counter=0):
    # We exclude LMSM Groups from check, because we don't sync them with PRP
    last_modified_instance = Realm.objects.filter(user_id=user_pk).exclude(group__name__in=LMSMPermissionsService.LMSM_GROUPS).order_by('modified').last()
    if last_modified_instance and last_modified_instance.modified.timestamp() > last_modified_at_timestamp:
        # there were updates to user realms. skip
        return

    _partner_realms = Realm.objects.filter(user_id=user_pk, group__name__in=PARTNER_ACTIVE_GROUPS)
    if not _partner_realms.exists():
        logger.info('No partner roles exist in user realms. Skipping..')
        return

    user = User.objects.filter(pk=user_pk).prefetch_related(Prefetch('realms', _partner_realms.filter(is_active=True).select_related('country', 'organization', 'group'))).get()

    data = PRPSyncUserSerializer(instance=user).data

    try:
        PRPAPI().send_user_realms(data)
    except HTTPError as ex:
        if retry_counter < 2:
            logger.info(f'Received {ex} from prp api. retrying')
            sync_realms_to_prp.apply_async(
                (user_pk, last_modified_at_timestamp),
                {'retry_counter': retry_counter + 1},
                eta=timezone.now() + datetime.timedelta(minutes=1 + retry_counter)
            )
        else:
            logger.exception(f'Received {ex} from prp api while trying to send realms after 3 attempts. '
                             f'User pk: {user_pk}.')


@app.task
def deactivate_stale_users():
    active_users = User.objects.filter(is_active=True)
    non_unicef_users = active_users.exclude(email__endswith=settings.UNICEF_USER_EMAIL)
    users_to_deactivate = non_unicef_users.filter(
        last_login__lt=timezone.now() - datetime.timedelta(days=settings.STALE_USERS_DEACTIVATION_THRESHOLD_DAYS),
    )
    for user in users_to_deactivate:
        logger.info(f'Deactivated user as it was inactive for more than 3 months: {user.email}')
        # save one by one instead of .update(is_active=True) to enable signals/save events
        user.is_active = False
        user.save()
