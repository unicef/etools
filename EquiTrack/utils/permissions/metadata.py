from __future__ import absolute_import, division, print_function, unicode_literals


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
        if serializer.context['request'].method == 'GET':
            filtered_fields = [f.field_name for f in serializer._readable_fields]
        else:
            filtered_fields = [f.field_name for f in serializer._writable_fields]

        for field_name in list(info.keys()):
            if field_name not in filtered_fields:
                del info[field_name]

        for field in info.values():
            self._remove_read_only(field)

        return info
