from django_fsm import transition as transition_wrapper


class ProtectUnknownTransitionsMeta(type):
    """
    Metaclass to disallow all transitions except defined ones
    """

    def __new__(cls, name, bases, new_attrs, **kwargs):
        status_field = new_attrs['status']

        choices = dict(status_field.choices).keys()
        statuses_matrix = {
            (source, target): False for source in choices for target in choices if source != target
        }

        for attr in new_attrs.values():
            if not hasattr(attr, '_django_fsm'):
                continue

            for transition in attr._django_fsm.transitions.values():
                statuses_matrix[(transition.source, transition.target)] = True

        for transition, known in statuses_matrix.items():
            if known:
                continue

            def new_transition(self):
                pass
            new_transition.__name__ = 'transition_{}_{}'.format(*transition)

            def access_denied_permission(instance, user):
                return False

            new_attrs[new_transition.__name__] = transition_wrapper(
                'status', transition[0], target=transition[1], permission=access_denied_permission
            )(new_transition)

        return super().__new__(cls, name, bases, new_attrs, **kwargs)


class EmptyQuerysetForExternal:
    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_unicef_user():
            return queryset.none()

        return queryset
