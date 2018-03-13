from __future__ import absolute_import

from utils.common.metadata import FSMTransitionActionMetadataMixin


class PermittedFSMTransitionActionMetadataMixin(FSMTransitionActionMetadataMixin):
    def determine_actions(self, request, view):
        request.user._permission_context = view._collect_permission_context()

        return super(PermittedFSMTransitionActionMetadataMixin, self).determine_actions(request, view)
