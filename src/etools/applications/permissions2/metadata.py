from rest_framework.metadata import SimpleMetadata
from unicef_restlib.metadata import (
    CRUActionsMetadataMixin,
    FSMTransitionActionMetadataMixin,
    ModelChoiceFieldMixin,
    ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,
)

from etools.applications.utils.permissions.metadata import PermissionsBasedMetadataMixin


class PermittedFSMTransitionActionMetadataMixin(FSMTransitionActionMetadataMixin):
    """
    Return list of available FSM transitions based on defined permissions.
    """

    def determine_actions(self, request, view):
        """
        Collect context for permissions and determine allowed actions based on it.
        :param request:
        :param view:
        :return:
        """
        request.user._permission_context = view._collect_permission_context()

        return super(PermittedFSMTransitionActionMetadataMixin, self).determine_actions(request, view)


class BaseMetadata(ReadOnlyFieldWithChoicesMixin, ModelChoiceFieldMixin, SeparatedReadWriteFieldMetadata,
                   CRUActionsMetadataMixin, SimpleMetadata):
    """Base metadata class"""


class PermissionBasedMetadata(PermittedFSMTransitionActionMetadataMixin, PermissionsBasedMetadataMixin, BaseMetadata):
    """Base metadata class handling permissions"""
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super().get_serializer_info(serializer)
