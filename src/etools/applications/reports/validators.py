import json
import re
from decimal import Decimal, InvalidOperation

from django import forms

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
                raise forms.ValidationError("Invalid number")
