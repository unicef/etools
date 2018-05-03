from __future__ import absolute_import, division, print_function, unicode_literals

import urllib

from django.core.urlresolvers import reverse
from django.db import connection
from django.utils.http import urlquote

from EquiTrack.utils import get_current_site
from users.models import Country


def site_url():
    return 'https://{0}'.format(
        get_current_site().domain
    )


def build_frontend_url(*parts):
    from email_auth.utils import update_url_with_kwargs

    token_auth_view = reverse('email_auth:login')
    change_country_view = urllib.parse.quote_plus(update_url_with_kwargs(
        reverse('users:country-change'),
        country=Country.objects.get(schema_name=connection.schema_name).id,
        next=urlquote('/'.join(map(str, ('',) + parts)))
    ))

    return '{domain}{token_auth_view}?next={change_country_view}'.format(
        domain=site_url(),
        token_auth_view=token_auth_view,
        change_country_view=change_country_view,
    )
