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


class TenantSuffixedString:
    """
    could be used to provide tenant-unique string
    """

    def __init__(self, value='', delimiter='.'):
        self.value = value
        self.delimiter = delimiter

    @staticmethod
    def get_tenant_suffix():
        return connection.tenant.country_short_code or ''

    def __str__(self):
        return f'{self.value}{self.delimiter}{self.get_tenant_suffix()}'
