from rest_framework.metadata import SimpleMetadata

from etools.applications.permissions2.metadata import PermittedFSMTransitionActionMetadataMixin
from etools.applications.rest_extra.metadata import (
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
)
from etools.applications.permissions.metadata import PermissionsBasedMetadataMixin


class ActionPointMetadata(
    PermittedFSMTransitionActionMetadataMixin,
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
