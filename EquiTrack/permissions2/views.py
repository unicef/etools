from __future__ import absolute_import

from rest_framework import serializers

from utils.common.views import FSMTransitionActionMixin


class PermissionContextMixin(object):
    def _collect_permission_context(self, instance=None):
        context = self.get_permission_context()

        if instance:
            context.extend(self.get_obj_permission_context(instance))

        if hasattr(self, 'get_parent'):
            context += self.get_parent()._collect_permission_context(self.get_parent_object())
        return context

    def get_permission_context(self):
        return []

    def get_obj_permission_context(self, obj):
        return []


class PermittedFSMActionMixin(PermissionContextMixin, FSMTransitionActionMixin):
    def check_transition_permission(self, transition, user):
        im_self = getattr(transition, 'im_self', getattr(transition, '__self__'))
        user._permission_context = self._collect_permission_context(instance=im_self)
        return super(PermittedFSMActionMixin, self).check_transition_permission(transition, user)


class PermittedSerializerMixin(PermissionContextMixin):
    def check_serializer_permissions(self, serializer, edit=False):
        if isinstance(serializer, serializers.ListSerializer):
            serializer = serializer.child

        if not edit and not serializer._readable_fields:
            self.permission_denied(self.request)

        if edit and not serializer._writable_fields:
            self.permission_denied(self.request)

    def get_serializer(self, instance=None, *args, **kwargs):
        many = kwargs.get('many', False)

        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        kwargs['context']['permission_context'] = self._collect_permission_context(not many and instance)

        serializer = serializer_class(instance, *args, **kwargs)

        self.check_serializer_permissions(serializer)

        return serializer

    def perform_create(self, serializer):
        self.check_serializer_permissions(serializer, edit=True)

        super(PermittedSerializerMixin, self).perform_create(serializer)

    def perform_update(self, serializer):
        self.check_serializer_permissions(serializer, edit=True)

        super(PermittedSerializerMixin, self).perform_update(serializer)
