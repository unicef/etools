from decimal import Decimal

from etools.applications.offline.errors import BadValueError, ValueTypeMismatch
from etools.applications.offline.validations.base import BaseValidation


class NumberValidation(BaseValidation):
    name = 'number'

    def validate(self, value):
        if not isinstance(value, (int, float, Decimal)):
            raise ValueTypeMismatch(value)


class IntegerValidation(NumberValidation):
    name = 'integer'

    def validate(self, value):
        if not isinstance(value, int):
            raise BadValueError(value)


class LessThanValidation(NumberValidation):
    name = 'lt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def validate(self, value):
        if self.allow_equality:
            if value <= self.threshold:
                return
        else:
            if value < self.threshold:
                return

        raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)


class GreaterThanValidation(BaseValidation):
    validation_type = 'number'
    name = 'gt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def validate(self, value):
        if self.allow_equality:
            if value >= self.threshold:
                return
        else:
            if value > self.threshold:
                return

        raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)
