import csv
import logging
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from .models import User, UserProfile, Country
try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError:
    class SiteProfileNotAvailable(Exception):
        pass



user_fields = [
    'dn',
    'upn',
    'displayName',
    'functionalTitle',
    'gender',
    'email',
    'givenName',
    'sn'
]

attr_map = {
    'dn': 'dn',
    'mail': 'username',
    'internetaddress': 'email',
    'givenName': 'first_name',
    'sn': 'last_name',
    'telephoneNumber': 'phone_number'
}


def _set_attribute(obj, attr, value):
        """Set an attribute of an object to a specific value.
        Return True if the attribute was changed and False otherwise.
        """
        field = obj._meta.get_field_by_name(attr)
        if len(value) > field[0].max_length:
            cleaned_value = value[:field[0].max_length]
            logging.warn('The attribute "%s" was trimmed from "%s" to "%s"' %
                        (attr, value, cleaned_value))
        else:
            cleaned_value = value

        old_value = getattr(obj, attr)
        if cleaned_value != old_value:
            setattr(obj, attr, cleaned_value)
            return True

        return False


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

    if user_modified:
        print 'saving modified user'
        user.save()
    if profile_modified:
        print 'saving profile for: {} {}'.format(user, user.profile)
        profile.save()


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
