from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from utils.common.metadata import (
    CRUActionsMetadataMixin, FSMTransitionActionMetadataMixin, ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,)
from utils.permissions.metadata import PermissionsBasedMetadataMixin


class AuditBaseMetadata(
    ReadOnlyFieldWithChoicesMixin,
    ModelChoiceFieldMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):
    pass


class EngagementMetadata(
    FSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    AuditBaseMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(EngagementMetadata, self).get_serializer_info(serializer)
