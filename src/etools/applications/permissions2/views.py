from django.core.exceptions import ValidationError as CoreValidationError
from django.http import Http404

from django_fsm import can_proceed, has_transition_perm
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError

from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition


class FSMTransitionActionMixin:
    def get_transition(self, action, instance=None):
        if not instance:
            instance = self.get_object()

        instance_action = getattr(instance, action, None)
        if not instance_action or not hasattr(instance_action, '_django_fsm'):
            raise Http404

        return instance_action

    def check_transition_permission(self, transition, user):
        try:
            if not can_proceed(transition) or not has_transition_perm(transition, user):
                raise PermissionDenied
        except CoreValidationError as exc:
            raise ValidationError(dict([error for error in exc]))

    def get_transition_serializer_class(self, transition):
        fsm_meta = transition._django_fsm
        im_self = getattr(transition, 'im_self', getattr(transition, '__self__'))
        current_state = fsm_meta.field.get_state(im_self)
        return fsm_meta.get_transition(current_state).custom.get('serializer')

    def pre_transition(self, instance, action):
        """
        hook to implement custom logic before transition
        """
        pass

    def post_transition(self, instance, action):
        """
        hook to implement custom logic after transition
        """
        pass

    @action(detail=True, methods=['post'], url_path=r'(?P<action>\D+)')
    def transition(self, request, *args, **kwargs):
        """
        Change status of FSM controlled object
        """
        action = kwargs.get('action', False)
        instance = self.get_object()
        instance_action = self.get_transition(action, instance)

        self.pre_transition(instance, action)

        self.check_transition_permission(instance_action, request.user)

        transition_serializer = self.get_transition_serializer_class(instance_action)
        if transition_serializer:
            serializer = transition_serializer(
                instance=instance,
                data=request.data,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            instance_action(**serializer.validated_data)
        else:
            instance_action()

        instance.save()

        self.post_transition(instance, action)

        return self.retrieve(request, *args, **kwargs)


class PermissionContextMixin:
    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            return

        # generate fake object in case of accessing nested
        if self.kwargs[lookup_url_kwarg] == 'new':  # trick to find the creation
            return self.queryset.model()

        return super().get_object()

    def _collect_permission_context(self, instance=None):
        context = self.get_permission_context()

        if not instance and hasattr(self, 'get_object'):
            try:
                instance = self.get_object()
            except AssertionError:
                pass

        if instance:
            if instance.pk:
                context.extend(self.get_obj_permission_context(instance))
            else:
                context.extend(self.get_new_obj_permission_context())
        elif getattr(self, 'action', None) == 'create':
            context.extend(self.get_new_obj_permission_context())

        if hasattr(self, 'get_parent'):
            context += self.get_parent()._collect_permission_context(self.get_parent_object())
        return context

    def get_permission_context(self):
        """independent of the instance"""
        return [
            GroupCondition(self.request.user),
        ]

    def get_new_obj_permission_context(self):
        """new instance"""
        return [
            NewObjectCondition(self.queryset.model)
        ]

    def get_obj_permission_context(self, obj):
        """object permissions"""
        return []


class PermittedFSMActionMixin(PermissionContextMixin, FSMTransitionActionMixin):
    """ """
    def check_transition_permission(self, transition, user):
        im_self = getattr(transition, 'im_self', getattr(transition, '__self__'))
        user._permission_context = self._collect_permission_context(instance=im_self)
        return super().check_transition_permission(transition, user)


class PermittedSerializerMixin(PermissionContextMixin):
    def check_serializer_permissions(self, serializer, edit=False):
        if isinstance(serializer, serializers.ListSerializer):
            serializer = serializer.child

        if not edit and not serializer._readable_fields:
            self.permission_denied(self.request)

        if edit and not serializer._writable_fields:
            self.permission_denied(self.request)

    def get_serializer(self, instance=None, serializer_class=None, *args, **kwargs):
        many = kwargs.get('many', False)

        serializer_class = serializer_class or self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        kwargs['context']['permission_context'] = self._collect_permission_context(not many and instance)

        serializer = serializer_class(instance, *args, **kwargs)

        self.check_serializer_permissions(serializer)

        return serializer

    def perform_create(self, serializer):
        self.check_serializer_permissions(serializer, edit=True)

        super().perform_create(serializer)

    def perform_update(self, serializer):
        self.check_serializer_permissions(serializer, edit=True)

        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self.check_serializer_permissions(self.get_serializer(instance=instance), edit=True)

        super().perform_destroy(instance)
