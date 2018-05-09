from rest_framework.metadata import SimpleMetadata

from etools.applications.attachments.metadata import ModelChoiceFieldMixin
from etools.applications.permissions.metadata import PermissionsBasedMetadataMixin
from etools.applications.rest_extra.metadata import (
    CRUActionsMetadataMixin,
    FSMTransitionActionMetadataMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
)


class TPMBaseMetadata(
    ReadOnlyFieldWithChoicesMixin,
    ModelChoiceFieldMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):
    pass


class TPMPermissionBasedMetadata(
    FSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    TPMBaseMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(TPMPermissionBasedMetadata, self).get_serializer_info(serializer)
