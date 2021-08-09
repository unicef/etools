from .exceptions import DetailedTransitionError, DetailedStateValidationError, DetailedBasicValidationError


def _is_decorated_response(result):
    return isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool)


def error_dict(function):
    def wrapper(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except DetailedBasicValidationError as e:
            return (False, [e.details])
        else:
            if _is_decorated_response(result):
                # we have result from previous decorator
                return result

            # this is result from original method
            if result and type(result) is bool:
                return (True, [])
            else:
                return (False, [function.__name__])

    return wrapper


def transition_error_dict(function):
    def wrapper(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except DetailedTransitionError as e:
            return (False, [e.details])

        if _is_decorated_response(result):
            # we have result from previous decorator
            return result

        # this is result from original method
        if result and type(result) is bool:
            return (True, [])
        else:
            return (False, ['generic_transition_fail'])

    return wrapper


def state_error_dict(function):
    def wrapper(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except DetailedStateValidationError as e:
            return (False, [e.details])

        if _is_decorated_response(result):
            # we have result from previous decorator
            return result

        # this is result from original method
        if result and type(result) is bool:
            return (True, [])
        else:
            return (False, ['generic_state_validation_fail'])

    return wrapper
