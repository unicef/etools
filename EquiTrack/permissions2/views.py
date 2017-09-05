from __future__ import absolute_import

from utils.common.views import FSMTransitionActionMixin


class PermissionContextMixin(object):
    def get_permission_context(self):
        context = self.extra_permission_context()
        if hasattr(self, 'parent'):
            context += self.get_parent().get_permission_context()
        return context

    def extra_permission_context(self):
        return []


class PermittedFSMActionMixin(PermissionContextMixin, FSMTransitionActionMixin):
    def check_transition_permission(self, transition, user):
        im_self = getattr(transition, 'im_self', getattr(transition, '__self__'))
        im_self._permission_context = self.get_permission_context()
        return super(PermittedFSMActionMixin, self).check_transition_permission(transition, user)


class PermittedSerializerMixin(PermissionContextMixin):
    def get_serializer_context(self):
        context = super(PermittedSerializerMixin, self).get_serializer_context()
        context['permission_context'] = self.get_permission_context()
        return context
