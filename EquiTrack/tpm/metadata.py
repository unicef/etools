from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from utils.common.metadata import FSMTransitionActionMetadataMixin, CRUActionsMetadataMixin
from utils.permissions.metadata import PermissionsBasedMetadataMixin


class TPMMetadata(FSMTransitionActionMetadataMixin,
                  PermissionsBasedMetadataMixin,
                  ModelChoiceFieldMixin,
                  CRUActionsMetadataMixin,
                  SimpleMetadata):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(TPMMetadata, self).get_serializer_info(serializer)
