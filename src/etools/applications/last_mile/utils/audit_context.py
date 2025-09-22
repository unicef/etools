import threading

from .user_detection import get_current_user

_audit_context = threading.local()


def set_audit_user(user):
    _audit_context.user = user


def get_audit_user():
    return getattr(_audit_context, 'user', get_current_user())


class audit_context:

    def __init__(self, user):
        self.user = user
        self.previous_user = None

    def __enter__(self):
        self.previous_user = get_audit_user()
        set_audit_user(self.user)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_audit_user(self.previous_user)
