from django.core.cache.backends.locmem import LocMemCache

from etools.libraries.cache_keys.locmemcache import KeysListLocMemCacheMixin


class eToolsLocMemCache(KeysListLocMemCacheMixin, LocMemCache):
    pass
