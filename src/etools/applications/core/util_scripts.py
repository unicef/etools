import logging
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.db.models import Q

from humanize import intcomma

from etools.applications.users.models import Country, UserProfile

logger = logging.getLogger(__name__)


def printtf(*args):
    file_name = 'mylogs.txt'
    args_list = [str(arg) for arg in args]
    logger.info(args_list)
    with open(file_name, 'ab') as f:
        f.write(', '.join(args_list))
        f.write('\n')


def set_country(name):
    country = Country.objects.get(Q(name=name) | Q(country_short_code=name) | Q(schema_name=name))
    connection.set_tenant(country)
    logger.info(f'Set in {country.name} workspace')


def local_country_keep():
    set_country('Global')
    keeping = ['Global', 'UAT', 'Lebanon', 'Syria', 'Indonesia', 'Sudan', 'Syria Cross Border', 'Pakistan']
    Country.objects.exclude(name__in=keeping).all().delete()


def create_test_user(email, password):
    country = Country.objects.get(name='UAT')
    g = Group.objects.get(name='UNICEF User')

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise Exception("Not a valid email")

    User = get_user_model()
    u = User(username=email, email=email)
    u.first_name = email.split("@")[0]
    u.last_name = email.split("@")[0]
    u.set_password(password)
    u.is_superuser = True
    u.is_staff = True
    u.save()
    g.user_set.add(u)
    userp = UserProfile.objects.get(user=u)
    userp.countries_available = [1, 12, 2, 3, 4, 5, 6, 7, 8,
                                 9, 10, 11, 13, 14, 15, 16, 18,
                                 19, 20, 21, 22, 23, 24, 25, 26,
                                 27, 28, 29, 30, 31, 32, 34, 35,
                                 36, 37, 38, 39, 40, 42, 43, 44,
                                 45, 46, 47, 49, 50, 52, 53, 54, 55]
    userp.country = country
    userp.country_override = country
    userp.save()
    logger.info("user {} created".format(u.email))


def currency_format(value):
    if isinstance(value, (int, float, Decimal)):
        return "{:,.2f}".format(value)
    elif isinstance(value, str):
        return intcomma(value)
    return value
