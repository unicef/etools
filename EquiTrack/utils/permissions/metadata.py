class PermissionsBasedMetadataMixin(object):
    """
    Filter fields which user has no read permission to.
    """
    def get_serializer_info(self, serializer):
        info = super(PermissionsBasedMetadataMixin, self).get_serializer_info(serializer)
        if serializer.context['request'].method == 'GET':
            filtered_fields = map(lambda f: f.field_name, serializer._readable_fields)
        else:
            filtered_fields = map(lambda f: f.field_name, serializer._writable_fields)

        for field_name in info.keys():
            if field_name not in filtered_fields:
                del info[field_name]
        return info
