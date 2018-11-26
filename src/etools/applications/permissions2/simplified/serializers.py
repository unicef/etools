from django.core.exceptions import PermissionDenied


class SafeReadOnlySerializerMixin(object):
    @property
    def _writable_fields(self):
        return [] if self.read_only else super()._writable_fields

    def is_valid(self, **kwargs):
        if not self._writable_fields:
            raise PermissionDenied

        return super().is_valid(**kwargs)
