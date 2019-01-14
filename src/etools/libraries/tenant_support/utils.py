import logging

from django.conf import settings
from django.db import connection
from django.db.models import Q

from django_tenants.utils import get_tenant_model

logger = logging.getLogger(__name__)


def set_country(user, request):

    country = request.GET.get(settings.SCHEMA_OVERRIDE_PARAM, None)
    if country:
        try:
            country = get_tenant_model().objects.get(Q(name=country) | Q(country_short_code=country) | Q(schema_name=country))
            if country in user.profile.countries_available.all():
                country = country
            else:
                country = None
        except get_tenant_model().DoesNotExist:
            country = None

    request.tenant = country or user.profile.country or user.profile.country_override
    connection.set_tenant(request.tenant)


def set_workspace(name):
    connection.set_tenant(get_tenant_model().objects.get(name=name))
    logger.info(u'Set in {} workspace'.format(name))


class every_country:
    """
    Loop through every available available tenant/country, then revert back to whatever was set before.

    Example usage:

    with every_country() as c:
        for country in c:
            print(country.name)
            function()
    """
    original_country = None

    def __enter__(self):
        self.original_country = connection.tenant
        for c in get_tenant_model().objects.exclude(name='Global').all():
            connection.set_tenant(c)
            yield c

    def __exit__(self, type, value, traceback):
        connection.set_tenant(self.original_country)


def run_on_all_tenants(function, **kwargs):
    with every_country() as c:
        for country in c:
            function(**kwargs)


def local_country_keep():
    set_workspace('Global')
    keeping = ['Global', 'UAT', 'Lebanon', 'Syria', 'Indonesia', 'Sudan', 'Syria Cross Border', 'Pakistan']
    get_tenant_model().objects.exclude(name__in=keeping).all().delete()
