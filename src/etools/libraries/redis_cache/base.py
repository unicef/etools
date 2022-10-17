from redis.exceptions import ConnectionError
from redis_cache import RedisCache
from redis_cache.backends.base import DEFAULT_TIMEOUT

from etools.libraries.cache_keys.redis import KeysListRedisCacheMixin


class eToolsCache(KeysListRedisCacheMixin, RedisCache):
    def _get(self, client, key, default=None):
        try:
            value = super()._get(client, key, default)
        except ConnectionError:
            value = default
        return value

    def _set(self, client, key, value, timeout, _add_only=False):
        try:
            result = super()._set(client, key, value, timeout, _add_only)
        except ConnectionError:
            result = value
        return result

    def _delete_many(self, client, keys):
        try:
            super()._delete_many(client, keys)
        except ConnectionError:
            pass

    def _clear(self, client):
        try:
            super()._clear(client)
        except ConnectionError:
            pass

    def _get_many(self, client, original_keys, versioned_keys):
        try:
            data = super()._get_many(client, original_keys, versioned_keys)
        except ConnectionError:
            data = {}
        return data

    def _incr_version(self, client, old, new, original, delta, version):
        try:
            result = super()._incr_version(
                client,
                old,
                new,
                original,
                delta,
                version,
            )
        except ConnectionError:
            result = None
        return result

    def _delete_pattern(self, client, pattern):
        try:
            super()._delete_pattern(client, pattern)
        except ConnectionError:
            pass

    def get_or_set(
            self,
            key,
            func,
            timeout=DEFAULT_TIMEOUT,
            lock_timeout=None,
            stale_cache_timeout=None,
    ):
        try:
            value = super().get_or_set(
                key,
                func,
                timeout=timeout,
                lock_timeout=lock_timeout,
                stale_cache_timeout=stale_cache_timeout,
            )
        except ConnectionError:
            try:
                value = func()
            except Exception:
                raise
        return value

    def incr(self, key, delta=1):
        try:
            value = super().incr(key, delta=delta)
        except ConnectionError:
            value = delta
        return value

    def delete(self, key):
        try:
            result = super().delete(key)
        except ConnectionError:
            result = True
        return result
