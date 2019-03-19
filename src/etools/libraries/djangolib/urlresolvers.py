from urllib.parse import urljoin

from django.conf import settings


def build_absolute_url(url):
    if not url:
        return ''

    return urljoin(settings.HOST, url)
