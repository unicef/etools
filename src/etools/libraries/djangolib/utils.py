from itertools import chain

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.sites.models import Site


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


def is_user_in_groups(user, group_names):
    """Utility function; returns True if user is in ANY of the groups in the group_names list, False if the user
    is in none of them. Note that group_names should be a tuple or list, not a single string.
    """
    if user.is_superuser:
        return True
    if isinstance(group_names, str):
        # Anticipate common programming oversight.
        raise ValueError('group_names parameter must be a tuple or list, not a string')
    return user.groups.filter(name__in=group_names).exists()


def get_all_field_names(TheModel):
    """Return a list of all field names that are possible for this model (including reverse relation names).
    Any internal-only field names are not included.

    Replacement for MyModel._meta.get_all_field_names() which does not exist under Django 1.10.
    https://github.com/django/django/blob/stable/1.7.x/django/db/models/options.py#L422
    https://docs.djangoproject.com/en/1.10/ref/models/meta/#migrating-from-the-old-api
    """
    return list(set(chain.from_iterable(
        (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
        for field in TheModel._meta.get_fields()
        if not (field.many_to_one and field.related_model is None) and
        not isinstance(field, GenericForeignKey)
    )))


class temporary_disconnect_signal:

    def __init__(self, signal, receiver, sender, dispatch_uid=None):
        self.signal = signal
        self.receiver = receiver
        self.sender = sender
        self.dispatch_uid = dispatch_uid

    def __enter__(self):
        self.signal.disconnect(
            receiver=self.receiver,
            sender=self.sender,
            dispatch_uid=self.dispatch_uid,
        )

    def __exit__(self, type, value, traceback):
        self.signal.connect(
            receiver=self.receiver,
            sender=self.sender,
            dispatch_uid=self.dispatch_uid,
        )
