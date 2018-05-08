
from django.core.urlresolvers import reverse
from django.db import connection
from django.utils.http import urlquote

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.users.models import Country


def site_url():
    return 'https://{0}'.format(
        get_current_site().domain
    )


def build_frontend_url(*parts):
    from etools.applications.email_auth.utils import update_url_with_kwargs

    token_auth_view = reverse('email_auth:login')
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
