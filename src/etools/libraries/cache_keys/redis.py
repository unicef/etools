from redis_cache import RedisCache
from redis_cache.backends.base import get_client

from etools.libraries.cache_keys.base import KeysListCacheMixin


def set_default_cache_pattern_argument(func):
    # get_client decorator makes pattern mandatory and raises `missing 1 required positional argument: 'key'` otherwise
    # so that we provide it automatically if user calls cache.keys() with no arguments to list all cache keys
    # also, get_client inside adds version prefix to our pattern, so we keep pattern transformation unified
    def wrapper(self, *args, **kwargs):
        if len(args) == 0:
            args = ['*']
        return func(self, *args, **kwargs)
    return wrapper


class KeysListRedisCacheMixin(KeysListCacheMixin, RedisCache):
    @set_default_cache_pattern_argument
    @get_client()
    def keys(self, client, pattern, version=None):
        version_prefix = self.make_key('', version=version)
        version_prefix_len = len(version_prefix)
        keys = (k.decode('utf-8') for k in client.keys(pattern=pattern))
        return [
            key[version_prefix_len:]
            for key in keys
            if key.startswith(version_prefix)
        ]
