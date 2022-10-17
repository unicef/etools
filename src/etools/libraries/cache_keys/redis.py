from redis_cache import RedisCache
from redis_cache.backends.base import get_client

from etools.libraries.cache_keys.base import KeysListCacheMixin


class KeysListRedisCacheMixin(KeysListCacheMixin, RedisCache):
    @get_client()
    def keys(self, client, pattern='*', version=None):
        pattern = self.make_key(pattern, version=version)
        version_prefix = self.make_key('', version=version)
        version_prefix_len = len(version_prefix)
        return [
            key[version_prefix_len:] for key in client.keys(pattern=pattern)
            if key.startswith(version_prefix)
        ]
