def get_available_transitions(obj, user, status_field='status'):
    current_state = getattr(obj, status_field)

    actions = []
    for name in dir(obj):
        try:
            action = getattr(obj, name)
        except AttributeError:
            continue

        if not hasattr(action, '_django_fsm'):
            continue

        meta = action._django_fsm
        if meta.has_transition(current_state) and meta.has_transition_perm(obj, current_state, user):
            actions.append(meta.get_transition(current_state))

    return actions
