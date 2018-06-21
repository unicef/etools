from django.db import connection
from django.urls import reverse
from django.utils.http import urlquote

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.users.models import Country


def site_url():
    return 'https://{0}'.format(
        get_current_site().domain
    )


def build_frontend_url(*parts):
    from etools.applications.tokens.utils import update_url_with_kwargs

    token_auth_view = reverse('tokens:login')
    change_country_view = urlquote(update_url_with_kwargs(
        reverse('users:country-change'),
        country=Country.objects.get(schema_name=connection.schema_name).id,
        next=urlquote('/'.join(map(str, ('',) + parts)))
    ))

    return '{domain}{token_auth_view}?next={change_country_view}'.format(
        domain=site_url(),
        token_auth_view=token_auth_view,
        change_country_view=change_country_view,
    )
