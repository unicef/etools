
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.encoding import force_text

from rest_framework import exceptions
from rest_framework.fields import ChoiceField
from rest_framework.request import clone_request

from utils.common.serializers.fields import SeparatedReadWriteField


class SeparatedReadWriteFieldMetadata(object):
    """
    Mixin for providing correct information about SeparatedReadWriteField.
    """
    def get_field_info(self, field):
        if isinstance(field, SeparatedReadWriteField):
            if field.context['request'].method == 'GET':
                field = field.read_field or field.write_field
            else:
                field = field.write_field

        return super(SeparatedReadWriteFieldMetadata, self).get_field_info(field)


class FSMTransitionActionMetadataMixin(object):
    """
    Return list of available FSM transitions.
    """
    def _collect_actions(self, instance):
        actions = []
        attrs = dir(instance)
        for attr in attrs:
            instance_action = getattr(instance, attr, None)
            if instance_action and hasattr(instance_action, '_django_fsm'):
                actions.append(instance_action)
        return actions

    def _get_instance(self, view):
        if hasattr(view, 'kwargs') and view.kwargs and 'pk' in view.kwargs:
            return self.get_object(view.queryset.model, view.kwargs["pk"])

    def get_object(self, model, pk):
        obj = get_object_or_404(model.objects.all(), pk=pk)
        return obj

    def determine_actions(self, request, view):
        actions = super(FSMTransitionActionMetadataMixin, self).determine_actions(request, view)
        instance = self._get_instance(view)
        if not instance:
            return actions

        allowed_FSM_transitions = []
        for action in self._collect_actions(instance):
            meta = action._django_fsm
            im_self = getattr(action, 'im_self', getattr(action, '__self__'))
            current_state = meta.field.get_state(im_self)

            if meta.has_transition(current_state) and meta.has_transition_perm(im_self, current_state, request.user):
                field_name = meta.field if isinstance(meta.field, six.string_types) else meta.field.name
                transition = meta.get_transition(getattr(instance, field_name))

                name = transition.custom.get('name', transition.name)
                if callable(name):
                    name = name(instance)

                allowed_FSM_transitions.append({
                    'code': action.__name__,
                    'display_name': name
                })

        # Move cancel to the end.
        actions["allowed_FSM_transitions"] = sorted(
            allowed_FSM_transitions, key=lambda a: a['code'] == 'cancel'
        )

        return actions


class CRUActionsMetadataMixin(object):
    """
    Return "GET" with readable fields as allowed method.
    """

    actions = {
        'PUT': 'update',
        'POST': 'create',
        'GET': 'retrieve'
    }

    def determine_actions(self, request, view):
        """
        For generic class based views we return information about
        the fields that are accepted for 'PUT' and 'POST' methods.
        """
        actions = {}
        for method in {'PUT', 'POST', 'GET'} & set(view.allowed_methods):
            view.request = clone_request(request, method)
            view.action = self.actions[method]
            instance = None
            try:
                # Test global permissions
                if hasattr(view, 'check_permissions'):
                    view.check_permissions(view.request)
                # Test object permissions
                lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
                if lookup_url_kwarg in view.kwargs and hasattr(view, 'get_object'):
                    instance = view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be supplied.
                serializer = view.get_serializer(instance=instance)
                actions[method] = self.get_serializer_info(serializer)
            finally:
                view.request = request

        return actions


class ReadOnlyFieldWithChoicesMixin(object):
    """
    Return choices for read only fields.
    """
    def get_field_info(self, field):
        field_info = super(ReadOnlyFieldWithChoicesMixin, self).get_field_info(field)
        if isinstance(field, ChoiceField) and hasattr(field, 'choices'):
            field_info['choices'] = [
                {
                    'value': choice_value,
                    'display_name': force_text(choice_name, strings_only=True)
                }
                for choice_value, choice_name in field.choices.items()
            ]
        return field_info
