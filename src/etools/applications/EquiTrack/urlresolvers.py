from django.conf import settings
from django.db import connection
from django.urls import reverse

from django_tenants.utils import get_tenant_model

from etools.libraries.pythonlib.urlresolvers import update_url_with_kwargs


def build_frontend_url(*parts, user=None):

    if not user or user.is_staff:
        frontend_url = '{}{}'.format(settings.HOST, reverse('main'))
    else:
        frontend_url = '{}{}'.format(settings.HOST, reverse('social:begin', kwargs={'backend': 'azuread-b2c-oauth2'}))

    change_country_view = update_url_with_kwargs(
        reverse('users:country-change'),
        country=get_tenant_model().objects.get(schema_name=connection.schema_name).id,
        next='/'.join(map(str, ('',) + parts))
    )

    frontend_url = update_url_with_kwargs(frontend_url, next=change_country_view)

    return frontend_url
