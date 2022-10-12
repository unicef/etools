from django.core.cache import caches, DEFAULT_CACHE_ALIAS


def invalidate_view_cache(key_prefix, cache_alias=None):
    """
    invalidates cache created by django.views.decorators.cache.cache_page
    url as well as context are variable, depending on url parameters, so wildcard them out and rely on key prefix only
    key example:
    views.decorators.cache.cache_page.fm-sites.NPL.GET.26d04fa6a67a4cb34885a9c5b1206e39.d96d7cd887705ba571615e93962d710e.en-us.UTC
    """
    page_cache_pattern = 'views.decorators.cache.cache_page.{0}.*'.format(key_prefix)
    headers_cache_pattern = 'views.decorators.cache.cache_header.{0}.*'.format(key_prefix)
    cache = caches[cache_alias or DEFAULT_CACHE_ALIAS]
    cache.delete_many(cache.keys(page_cache_pattern))
    cache.delete_many(cache.keys(headers_cache_pattern))
