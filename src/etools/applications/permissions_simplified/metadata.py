from unicef_restlib.metadata import FSMTransitionActionMetadataMixin

from etools.applications.permissions2.metadata import PermissionsBasedMetadataMixin, BaseMetadata
from etools.applications.permissions_simplified.views import SimplePermittedFSMTransitionActionMixin


class SimplifiedFSMTransitionActionMetadataMixin(FSMTransitionActionMetadataMixin):
    def _is_action_allowed(self, instance, request, view, action):
        if not isinstance(view, SimplePermittedFSMTransitionActionMixin):
            return True

        if isinstance(action, dict):
            action = action['code']

        transition_permissions = view.get_transition_permissions(action)
        allow_action = transition_permissions and all(permission.has_permission(request, view) and
                                                      permission.has_object_permission(request, view, instance)
                                                      for permission in transition_permissions)

        return allow_action

    def determine_actions(self, request, view):
        metadata = super().determine_actions(request, view)
        if 'allowed_FSM_transitions' not in metadata:
            return metadata

        instance = self._get_instance(view)
        metadata['allowed_FSM_transitions'] = [
            action for action in metadata['allowed_FSM_transitions']
            if self._is_action_allowed(instance, request, view, action)
        ]
        return metadata


class SimplePermissionBasedMetadata(SimplifiedFSMTransitionActionMetadataMixin, PermissionsBasedMetadataMixin, BaseMetadata):
    """Base metadata class handling permissions"""
    pass
