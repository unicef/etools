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
            filtered_fields = map(lambda f: f.field_name, serializer._readable_fields)
        else:
            filtered_fields = map(lambda f: f.field_name, serializer._writable_fields)

        for field_name in info.keys():
            if field_name not in filtered_fields:
                del info[field_name]

        for field in info.values():
            self._remove_read_only(field)

        return info
