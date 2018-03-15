from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.urlresolvers import reverse
from drfpasswordless.utils import create_callback_token_for_user

from future.backports.urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin

from utils.common.urlresolvers import site_url


def update_url_with_kwargs(url, **kwargs):
    if not url:
        return

    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(kwargs)
    url_parts[4] = urlencode(query)

    return urlunparse(url_parts)


def get_token_auth_link(user):
    token = create_callback_token_for_user(user, 'email')
    return update_url_with_kwargs(urljoin(site_url(), reverse('email_auth:login')), token=token)
