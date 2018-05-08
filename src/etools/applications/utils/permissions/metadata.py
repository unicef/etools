
from django.utils import six


class PermissionsBasedMetadataMixin(object):
    """
    Filter fields which user has no read permission to.
    """

    def _remove_read_only(self, field_info):
        field_info.pop('read_only', None)

        if 'child' in field_info:
            self._remove_read_only(field_info['child'])

        if 'children' in field_info:
            for field in field_info['children'].values():
                self._remove_read_only(field)

    def get_serializer_info(self, serializer):
        info = super(PermissionsBasedMetadataMixin, self).get_serializer_info(serializer)
        method = serializer.context['request'].method
        fields = serializer._readable_fields if method == 'GET' else serializer._writable_fields
        field_names = [f.field_name for f in fields]
        info = {k: v for k, v in six.iteritems(info) if k in field_names}

        for field in info.values():
            self._remove_read_only(field)

        return info
