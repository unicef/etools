from django.core.exceptions import ValidationError as CoreValidationError
from django.http import Http404

from django_fsm import can_proceed, has_transition_perm
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError


class FSMTransitionActionMixin(object):
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
            serializer = transition_serializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            instance_action(**serializer.validated_data)
        else:
            instance_action()

        instance.save()

        self.post_transition(instance, action)

        return self.retrieve(request, *args, **kwargs)
