import hashlib

from django.conf import settings
from django.core.cache import caches


class CachedListViewSetMixin:
    list_cache_alias = None
    list_cache_prefix = None
    list_cache_timeout = 60 * 60 * 24  # one day

    @classmethod
    def get_cache(cls):
        if cls.list_cache_alias:
            return caches[cls.list_cache_alias]
        return caches[settings.CACHE_MIDDLEWARE_ALIAS]

    def use_cache(self, request):
        # no easy way to invalidate paginated pages, so no such logic at the moment
        if request.method != 'GET':
            return False
        return True

    @classmethod
    def get_view_cache_key(cls, full_path):
        # similar to django.utils.cache._generate_cache_key, just with no headers info and tz/i18n
        # since cache can differ, we have no functionality like cache.keys to match wildcard,
        # so need to make path static
        key_prefix = cls.list_cache_prefix or ''
        url = hashlib.md5(full_path.encode('ascii'))
        return 'etools.libraries.views.cache.%s.%s' % (key_prefix, url.hexdigest())

    def list(self, request, *args, **kwargs):
        cache = self.get_cache()
        cache_key = self.get_view_cache_key(request.get_full_path())
        use_cache = self.use_cache(request)
        if use_cache:
            cached_response = cache.get(cache_key)
            if cached_response:
                # hit, return cached response
                return cached_response

        response = super().list(request, *args, **kwargs)

        if response.status_code == 200:
            # don't cache failed requests
            if hasattr(response, 'render') and callable(response.render):
                response.add_post_render_callback(
                    lambda r: cache.set(cache_key, r, timeout=self.list_cache_timeout)
                )
            else:
                cache.set(cache_key, response, timeout=self.list_cache_timeout)

        return response

    @classmethod
    def invalidate_view_cache(cls, full_path):
        cache_key = cls.get_view_cache_key(full_path)
        cache = cls.get_cache()

        cache.delete(cache_key)
