import inspect


def get_current_user_from_stack():
    frame = inspect.currentframe()
    try:
        while frame:
            local_vars = frame.f_locals

            if 'self' in local_vars:
                obj = local_vars['self']
                if hasattr(obj, 'request'):
                    request = obj.request
                    if hasattr(request, 'user') and request.user.is_authenticated:
                        return request.user

            if 'request' in local_vars:
                request = local_vars['request']
                if hasattr(request, 'user') and request.user.is_authenticated:
                    return request.user

            if 'user' in local_vars:
                user = local_vars['user']
                if hasattr(user, 'is_authenticated') and user.is_authenticated:
                    return user

            frame = frame.f_back
    finally:
        del frame

    return None


def get_current_user():
    user = get_current_user_from_stack()
    if user:
        return user
    return None
