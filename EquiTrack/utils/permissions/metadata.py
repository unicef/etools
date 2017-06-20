class PermissionsBasedMetadataMixin(object):
    def get_serializer_info(self, serializer):
        info = super(PermissionsBasedMetadataMixin, self).get_serializer_info(serializer)
        readable_fields = map(lambda f: f.field_name, serializer._readable_fields)

        for field_name in info.keys():
            if field_name not in readable_fields:
                del info[field_name]
        return info
