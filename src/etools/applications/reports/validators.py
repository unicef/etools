import json
import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.utils.translation import gettext as _

from rest_framework.exceptions import ValidationError
from rest_framework.utils.representation import smart_repr

re_allowed_chars = re.compile("^[0-9,.]+$")


def value_numbers(data):
    """Ensure that each value in json object is a number"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            raise forms.ValidationError("Invalid data")
    for v in data.values():
        try:
            Decimal(v)
        except (TypeError, InvalidOperation):
            if v and ',' in v:
                raise forms.ValidationError(
                    "Invalid format. Use '.' (dot) instead of ',' (comma) for decimal values.")
            raise forms.ValidationError("Invalid number")


def value_none_or_numbers(data):
    """Ensure that each value in json object is None or a number"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            raise forms.ValidationError("Invalid data")
    for v in data.values():
        if v is not None:
            try:
                Decimal(v)
            except (TypeError, InvalidOperation):
                if ',' in v:
                    raise forms.ValidationError(
                        "Invalid format. Use '.' (dot) instead of ',' (comma) for decimal values.")
                raise forms.ValidationError("Invalid number")


class SpecialReportingRequirementUniqueValidator:
    message = _("There is already a special report with this due date.")
    requires_context = True

    def __init__(self, queryset, message=None):
        self.queryset = queryset
        self.message = message or self.message
        self.intervention = None

    def __call__(self, attrs, serializer):

        instance = getattr(serializer, 'instance', None)
        qs = self.queryset
        if instance:
            qs = qs.exclude(pk=instance.pk)
        qs = qs.filter(
            intervention=attrs.get("intervention",  getattr(instance, 'intervention', None)),
            due_date=attrs["due_date"],
        )
        if qs.exists():
            raise ValidationError({"due_date": self.message}, code='unique')

    def __repr__(self):
        return '<{}(queryset={}, fields=due_date)>'.format(
            self.__class__.__name__,
            smart_repr(self.queryset),
        )
