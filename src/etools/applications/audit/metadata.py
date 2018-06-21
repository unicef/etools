from rest_framework.metadata import SimpleMetadata

from etools.applications.attachments.metadata import ModelChoiceFieldMixin
from etools.applications.permissions.metadata import PermissionsBasedMetadataMixin
from etools.applications.permissions2.metadata import PermittedFSMTransitionActionMetadataMixin
from etools.applications.rest_extra.metadata import (
    CRUActionsMetadataMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
)


class AuditBaseMetadata(
    ReadOnlyFieldWithChoicesMixin,
    ModelChoiceFieldMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):
    pass


class AuditPermissionBasedMetadata(
    PermittedFSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    AuditBaseMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(AuditPermissionBasedMetadata, self).get_serializer_info(serializer)
