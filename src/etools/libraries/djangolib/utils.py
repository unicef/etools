def is_user_in_groups(user, group_names):
    """Utility function; returns True if user is in ANY of the groups in the group_names list, False if the user
    is in none of them. Note that group_names should be a tuple or list, not a single string.
    """
    if isinstance(group_names, str):
        # Anticipate common programming oversight.
        raise ValueError('group_names parameter must be a tuple or list, not a string')
    return user.groups.filter(name__in=group_names).exists()
