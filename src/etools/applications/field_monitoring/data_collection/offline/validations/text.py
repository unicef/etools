import re

from etools.applications.field_monitoring.data_collection.offline.validations.base import BaseValidation


class TextValidation(BaseValidation):
    validation_type = 'text'
    name = 'text'

    def is_valid(self, value):
        return isinstance(value, str)


class MaxLengthTextValidation(BaseValidation):  # todo: inherit from text validation
    validation_type = 'text'
    name = 'max_length'

    def __init__(self, max_length, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def is_valid(self, value):
        return len(value) < self.max_length

    def to_dict(self, **kwargs):
        return super().to_dict(max_length=self.max_length, **kwargs)


class RegexTextValidation(BaseValidation):
    validation_type = 'text'
    name = 'regex'

    def __init__(self, regex, **kwargs):
        self.regex = regex
        super().__init__(**kwargs)

    def is_valid(self, value):
        return bool(re.match(self.regex, value))

    def to_dict(self, **kwargs):
        return super().to_dict(regex=self.regex, **kwargs)
