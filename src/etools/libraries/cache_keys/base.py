class KeysListCacheMixin:
    def keys(self, pattern='*', version=None):
        """
        get keys list based on pattern provided.
        pattern should support wildcard
        example: https://redis.io/commands/keys/
        """
        raise NotImplementedError
