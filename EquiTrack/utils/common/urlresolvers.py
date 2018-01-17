from __future__ import absolute_import, division, print_function, unicode_literals

from EquiTrack.utils import get_current_site
from django.utils.six.moves import map


def site_url():
    return 'https://{0}/'.format(
        get_current_site().domain
    )


def build_frontend_url(frontend_module, *parts):
    return site_url() + frontend_module + '/' + '/'.join(map(str, parts))
