from typing import Any

from django.utils.encoding import force_str

from etools.applications.offline.errors import ValueTypeMismatch
from etools.applications.offline.fields.base import BaseTypedField


class TextField(BaseTypedField):
    input_type = 'text'

    def cast_value(self, value: Any) -> str:
        return force_str(value)


class IntegerField(BaseTypedField):
    input_type = 'number-integer'

    def cast_value(self, value: Any) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueTypeMismatch(value)


class FloatField(BaseTypedField):
    input_type = 'number-float'

    def cast_value(self, value: Any) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueTypeMismatch(value)


class BooleanField(BaseTypedField):
    input_type = 'bool'

    def cast_value(self, value: Any) -> bool:
        if value in [True, 'True', 'true', '1', 'yes', 1]:
            return True
        return False
