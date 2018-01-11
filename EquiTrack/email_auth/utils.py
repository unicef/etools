from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from future.backports.urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from email_auth.models import SecurityToken


def update_url_with_token(url, user):
    if not url:
        return

    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update({settings.EMAIL_AUTH_TOKEN_NAME: SecurityToken.generate_token(user).token})
    url_parts[4] = urlencode(query)

    return urlunparse(url_parts)
