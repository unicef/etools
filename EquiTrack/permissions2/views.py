from __future__ import absolute_import

from utils.common.views import FSMTransitionActionMixin


class PermissionContextMixin(object):
    def _collect_permission_context(self):
        context = self.get_permission_context()

        if (self.lookup_url_kwarg or self.lookup_field) in self.kwargs:
            obj = self.get_object()
            context.extend(self.get_obj_permission_context(obj))

        if hasattr(self, 'get_parent'):
            context += self.get_parent()._collect_permission_context()
        return context

    def get_permission_context(self):
        return []

    def get_obj_permission_context(self, obj):
        return []


class PermittedFSMActionMixin(PermissionContextMixin, FSMTransitionActionMixin):
    def check_transition_permission(self, transition, user):
        user._permission_context = self._collect_permission_context()
        return super(PermittedFSMActionMixin, self).check_transition_permission(transition, user)


class PermittedSerializerMixin(PermissionContextMixin):
    def get_serializer_context(self):
        context = super(PermittedSerializerMixin, self).get_serializer_context()
        context['permission_context'] = self._collect_permission_context()
        return context
