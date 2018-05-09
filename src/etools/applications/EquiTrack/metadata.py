from __future__ import absolute_import, division, print_function, unicode_literals

from django.shortcuts import get_object_or_404
from django.utils import six


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
