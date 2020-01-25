from decimal import Decimal

from etools.applications.field_monitoring.data_collection.offline.validations.base import BaseValidation


class NumberValidation(BaseValidation):
    validation_type = 'number'
    name = 'number'

    def is_valid(self, value):
        return isinstance(value, (int, float, Decimal))


class IntValidation(BaseValidation):  # todo: inherit from number validation
    validation_type = 'number'
    name = 'int'

    def is_valid(self, value):
        return isinstance(value, int)


class LessThanValidation(BaseValidation):
    validation_type = 'number'
    name = 'lt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def is_valid(self, value):
        if self.allow_equality:
            return value <= self.threshold
        else:
            return value < self.threshold

    def to_dict(self, **kwargs):
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)


class GreaterThanValidation(BaseValidation):
    validation_type = 'number'
    name = 'gt'

    def __init__(self, threshold=None, allow_equality=True, **kwargs):
        self.threshold = threshold
        self.allow_equality = allow_equality
        super().__init__(**kwargs)

    def is_valid(self, value):
        if self.allow_equality:
            return value >= self.threshold
        else:
            return value > self.threshold

    def to_dict(self, **kwargs):
        return super().to_dict(threshold=self.threshold, allow_equality=self.allow_equality, **kwargs)
