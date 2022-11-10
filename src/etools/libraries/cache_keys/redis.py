from redis_cache import RedisCache

from etools.libraries.cache_keys.base import KeysListCacheMixin


class KeysListRedisCacheMixin(KeysListCacheMixin, RedisCache):
    def keys(self, pattern='*', version=None):
        versioned_pattern = self.make_key(pattern, version=version)
        client = self.get_client(versioned_pattern, write=False)
        version_prefix = self.make_key('', version=version)
        version_prefix_len = len(version_prefix)
        keys = (k.decode('utf-8') for k in client.keys(pattern=versioned_pattern))
        return [
            key[version_prefix_len:]
            for key in keys
            if key.startswith(version_prefix)
        ]
