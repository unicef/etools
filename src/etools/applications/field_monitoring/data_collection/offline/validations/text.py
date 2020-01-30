import re

from etools.applications.field_monitoring.data_collection.offline.validations.base import BaseValidation
from etools.applications.field_monitoring.data_collection.offline.validations.errors import (
    BadValueError,
    ValueTypeMismatch,
)


class TextValidation(BaseValidation):
    name = 'text'

    def validate(self, value):
        if not isinstance(value, str):
            raise ValueTypeMismatch(value)


class MaxLengthTextValidation(TextValidation):
    name = 'max_length'

    def __init__(self, max_length, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def is_valid(self, value):
        if not len(value) < self.max_length:
            raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(max_length=self.max_length, **kwargs)


class RegexTextValidation(TextValidation):
    name = 'regex'

    def __init__(self, regex, **kwargs):
        self.regex = regex
        super().__init__(**kwargs)

    def validate(self, value):
        if not bool(re.match(self.regex, value)):
            raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(regex=self.regex, **kwargs)
