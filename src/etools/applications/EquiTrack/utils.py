"""
Project wide base classes and utility functions for apps
"""
import codecs
import csv
import hashlib
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.cache import cache

from etools.applications.users.models import Country, UserProfile

logger = logging.getLogger(__name__)


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


def proccess_permissions(permission_dict):
    """
    :param permission_dict: the csv file read as a generator of dictionaries
     where the header contains the following keys:

    'Group' - the Django Group the user should belong to - field may be blank.
    'Condition' - the condition that should be required to satisfy.
    'Status' - the status of the model (represents state)
    'Field' - the field we are targetting (eg: start_date) this needs to be spelled exactly as it is on the model
    'Action' - One of the following values: 'view', 'edit', 'required'
    'Allowed' - the boolean 'TRUE' or 'FALSE' if the action should be allowed if the: group match, status match and
    condition match are all valid

    *** note that in order for the system to know what the default behaviour should be on a specified field for a
    specific action, only the conditions opposite to the default should be defined.

    :return:
     a nested dictionary where the first key is the field targeted, the following nested key is the action possible,
     and the last nested key is the action parameter
     eg:
     {'start_date': {'edit': {'false': [{'condition': 'condition2',
                                         'group': 'UNICEF USER',
                                         'status': 'Active'}]},
                     'required': {'true': [{'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Active'},
                                           {'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Signed'}]},
                     'view': {'true': [{'condition': 'condition1',
                                        'group': 'PM',
                                        'status': 'Active'}]}}}
    """

    result = Vividict()
    possible_actions = ['edit', 'required', 'view']

    for row in permission_dict:
        field = row['Field Name']
        action = row['Action'].lower()
        allowed = row['Allowed'].lower()
        assert action in possible_actions

        if isinstance(result[field][action][allowed], dict):
            result[field][action][allowed] = []

        # this action should not have been defined with any other allowed param
        assert list(result[field][action].keys()) == [allowed], \
            'There cannot be two types of "allowed" defined on the same ' \
            'field with the same action as the system will not be able' \
            ' to have a default behaviour.  field=%r, action=%r, allowed=%r' \
            % (field, action, allowed)

        result[field][action][allowed].append({
            'group': row['Group'],
            'condition': row['Condition'],
            'status': row['Status'].lower()
        })
    return result


def import_permissions(model_name):
    permission_file_map = {
        'Intervention': settings.PACKAGE_ROOT + '/assets/partner/intervention_permissions.csv',
        'Agreement': settings.PACKAGE_ROOT + '/assets/partner/agreement_permissions.csv'
    }

    def process_file():
        with codecs.open(permission_file_map[model_name], 'r', encoding='ascii') as csvfile:
            sheet = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            result = proccess_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    response = cache.get_or_set(cache_key, process_file, 60 * 60 * 24)

    return response


def get_current_year():
    return datetime.today().year


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.today()
    month = retrieve_date.month
    if 0 < month <= 3:
        quarter = 'q1'
    elif 3 < month <= 6:
        quarter = 'q2'
    elif 6 < month <= 9:
        quarter = 'q3'
    else:
        quarter = 'q4'
    return quarter


def h11(w):
    return hashlib.md5(w).hexdigest()[:9]


def is_user_in_groups(user, group_names):
    """Utility function; returns True if user is in ANY of the groups in the group_names list, False if the user
    is in none of them. Note that group_names should be a tuple or list, not a single string.
    """
    if isinstance(group_names, str):
        # Anticipate common programming oversight.
        raise ValueError('group_names parameter must be a tuple or list, not a string')
    return user.groups.filter(name__in=group_names).exists()


def to_choices_list(value):
    if isinstance(value, dict):
        return value.items()

    return value


def printtf(*args):
    """print function which write on file"""
    file_name = 'mylogs.txt'
    args_list = [str(arg) for arg in args]
    logger.info(args_list)
    with open(file_name, 'ab') as f:
        f.write(', '.join(args_list))
        f.write('\n')


def create_admin_user(username, password):
    """
    Creates a super user ready for working

    create_admin_user('macioce@unicef.org', 123)
    username -> macioce
    first_name -> Macioce
    last_name -> Macioce
    email -> macioce@unicef.org

    create_admin_user('dome.nico@unicef.org', 123)
    username -> dome.nico
    first_name -> Dome
    last_name -> Nico
    email -> dome.nico@unicef.org

    """
    groups = Group.objects.filter(name__in=['Partnership Manager', 'PME', 'Third Party Monitor', 'Travel Administrator',
                                            'Travel Focal Point', 'UNICEF Audit Focal Point', 'UNICEF User'])
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username, email=username + '@unicef.org', defaults={
        'first_name': username.split(".")[0].capitalize(),
        'last_name': username.split(".")[-1].capitalize(),
        'is_superuser': True,
        'is_staff': True,
    })
    user.groups.set(groups)
    user.set_password(password)
    user.save()
    profile = UserProfile.objects.get(user=user)
    country = Country.objects.get(name='Lebanon')
    countries = Country.objects.all()
    profile.country = country
    profile.country_override = country
    profile.countries_available.set(countries)
    profile.save()
    logger.info(u"user {} created".format(user.email))
