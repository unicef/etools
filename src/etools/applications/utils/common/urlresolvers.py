from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from django.conf import settings
from django.db import connection
from django.urls import reverse

from etools.applications.users.models import Country


def build_absolute_url(url):
    if not url:
        return ''

    return urljoin(settings.HOST, url)


def update_url_with_kwargs(url, **kwargs):
    if not url:
        return

    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(kwargs)
    url_parts[4] = urlencode(query)

    return urlunparse(url_parts)


def build_frontend_url(*parts, user=None, **kwargs):

    if not user or user.is_staff:
        frontend_url = '{}{}'.format(settings.HOST, reverse('main'))
    else:
        frontend_url = '{}{}'.format(settings.HOST, reverse('social:begin', kwargs={'backend': 'azuread-b2c-oauth2'}))

    change_country_view = update_url_with_kwargs(
        reverse('users:country-change'),
        country=Country.objects.get(schema_name=connection.schema_name).id,
        next='/'.join(map(str, ('',) + parts))
    )

    frontend_url = update_url_with_kwargs(frontend_url, next=change_country_view)

    return frontend_url
