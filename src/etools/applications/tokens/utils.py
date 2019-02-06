from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, urljoin

from django.conf import settings
from django.urls import reverse

from drfpasswordless.utils import create_callback_token_for_user


def update_url_with_kwargs(url, **kwargs):
    if not url:
        return

    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(kwargs)
    url_parts[4] = urlencode(query)

    return urlunparse(url_parts)


def update_url_with_auth_token(url, user):
    token = create_callback_token_for_user(user, 'email')
    return update_url_with_kwargs(url, **{settings.EMAIL_AUTH_TOKEN_NAME: token})


def get_token_auth_link(user):
    return update_url_with_auth_token(
        urljoin(settings.HOST, reverse('tokens:login')),
        user
    )
