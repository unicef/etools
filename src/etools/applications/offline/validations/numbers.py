from typing import Any

from etools.applications.offline.errors import BadValueError, ValueTypeMismatch
from etools.applications.offline.validations.base import BaseValidation


class NumberValidation(BaseValidation):
    def validate(self, value: Any) -> [int, float]:
        if not isinstance(value, (int, float)):
            raise ValueTypeMismatch(value)
        return value


class LessThanValidation(NumberValidation):
    name = 'lt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def validate(self, value: Any) -> [int, float]:
        value = super().validate(value)
        if self.allow_equality:
            if value <= self.threshold:
                return value
        else:
            if value < self.threshold:
                return value

        raise BadValueError(value)

    def to_dict(self, **kwargs) -> dict:
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)


class GreaterThanValidation(NumberValidation):
    name = 'gt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def validate(self, value: Any) -> [int, float]:
        value = super().validate(value)
        if self.allow_equality:
            if value >= self.threshold:
                return value
        else:
            if value > self.threshold:
                return value

        raise BadValueError(value)

    def to_dict(self, **kwargs) -> dict:
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)
