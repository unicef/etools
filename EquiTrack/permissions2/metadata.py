from utils.common.metadata import FSMTransitionActionMetadataMixin


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
        request.user._permission_context = view._collect_permission_context(instance=self._get_instance(view))

        return super(PermittedFSMTransitionActionMetadataMixin, self).determine_actions(request, view)
