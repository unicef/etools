from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError


class SafeReadOnlySerializerMixin(object):
    @property
    def _writable_fields(self):
        return [] if self.read_only else super()._writable_fields

    def is_valid(self, **kwargs):
        raise_exception = kwargs.get('raise_exception')
        if not self._writable_fields:
            if raise_exception:
                raise ValidationError(_('Unable to edit readonly serializer'))
            else:
                return False

        return super().is_valid(**kwargs)
