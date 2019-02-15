from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def update_url_with_kwargs(url, **kwargs):
    if not url:
        return

    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(kwargs)
    url_parts[4] = urlencode(query)

    return urlunparse(url_parts)
