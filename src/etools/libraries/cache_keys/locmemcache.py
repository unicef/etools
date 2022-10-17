from fnmatch import fnmatch

from django.core.cache.backends.locmem import LocMemCache

from etools.libraries.cache_keys.base import KeysListCacheMixin


class KeysListLocMemCacheMixin(KeysListCacheMixin, LocMemCache):
    def keys(self, pattern='*', version=None):
        pattern = self.make_key(pattern, version=version)
        version_prefix = self.make_key('', version=version)
        version_prefix_len = len(version_prefix)
        return [
            key[version_prefix_len:] for key in self._cache.keys()
            if fnmatch(key, pattern) and key.startswith(version_prefix)
        ]
