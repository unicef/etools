from django.db import connection
from django.urls import reverse

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.users.models import Country


def site_url():
    return 'https://{0}'.format(
        get_current_site().domain
    )


def build_frontend_url(*parts, user=None, include_token=False, **kwargs):
    from etools.applications.tokens.utils import update_url_with_kwargs, update_url_with_auth_token

    frontend_url = site_url()

    if not user or user.is_staff:
        frontend_url += reverse('main')
    else:
        frontend_url += reverse('tokens:login')

    change_country_view = update_url_with_kwargs(
        reverse('users:country-change'),
        country=Country.objects.get(schema_name=connection.schema_name).id,
        next='/'.join(map(str, ('',) + parts))
    )

    frontend_url = update_url_with_kwargs(frontend_url, next=change_country_view)

    if user and include_token:
        frontend_url = update_url_with_auth_token(frontend_url, user)

    return frontend_url
