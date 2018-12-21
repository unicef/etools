from etools.applications.permissions2.metadata import PermissionsBasedMetadataMixin, BaseMetadata


class PermissionBasedMetadata(PermissionsBasedMetadataMixin, BaseMetadata):
    """Base metadata class handling permissions"""
    def get_serializer_info(self, serializer):
        # if serializer.instance:
        #     serializer.context['instance'] = serializer.instance
        return super().get_serializer_info(serializer)
