from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from utils.common.metadata import FSMTransitionActionMetadataMixin, CRUActionsMetadataMixin, \
    ReadOnlyFieldWithChoicesMixin, SeparatedReadWriteFieldMetadata
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
    pass
