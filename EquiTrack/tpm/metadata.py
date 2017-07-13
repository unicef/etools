from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from utils.common.metadata import FSMTransitionActionMetadataMixin, CRUActionsMetadataMixin, \
    ReadOnlyFieldWithChoicesMixin, SeparatedReadWriteFieldMetadata
from utils.permissions.metadata import PermissionsBasedMetadataMixin


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
