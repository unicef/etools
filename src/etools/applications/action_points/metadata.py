from rest_framework.metadata import SimpleMetadata
from unicef_restlib.metadata import (
    CRUActionsMetadataMixin,
    ModelChoiceFieldMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
)

from etools.applications.permissions2.metadata import PermittedFSMTransitionActionMetadataMixin
from etools.applications.utils.permissions.metadata import PermissionsBasedMetadataMixin


class ActionPointMetadata(
    PermittedFSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    ModelChoiceFieldMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(ActionPointMetadata, self).get_serializer_info(serializer)
