from rest_framework.metadata import SimpleMetadata

from etools.applications.utils.common.metadata import FSMTransitionActionMetadataMixin, ReadOnlyFieldWithChoicesMixin, \
    SeparatedReadWriteFieldMetadata, CRUActionsMetadataMixin
from etools.applications.utils.permissions.metadata import PermissionsBasedMetadataMixin


class ActionPointMetadata(
    FSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(ActionPointMetadata, self).get_serializer_info(serializer)
