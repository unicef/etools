
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
    return '{domain}{change_country_view}?country={country_id}&next={next}'.format(
        domain=site_url(),
        change_country_view=reverse('users:country-change'),
        country_id=Country.objects.get(schema_name=connection.schema_name).id,
        next=urlquote('/'.join(map(str, ('',) + parts))),
    )
