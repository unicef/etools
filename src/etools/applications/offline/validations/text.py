import re

from django.utils.translation import gettext_lazy as _

from etools.applications.offline.errors import BadValueError, ValidationError, ValueTypeMismatch
from etools.applications.offline.validations.base import BaseValidation


class TextValidation(BaseValidation):
    def validate(self, value):
        if not isinstance(value, str):
            raise ValueTypeMismatch(value)


class MaxLengthTextValidation(TextValidation):
    name = 'max_length'

    def __init__(self, max_length, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def validate(self, value):
        super().validate(value)
        if not len(value) <= self.max_length:
            raise ValidationError(_('Ensure this field has no more than {0} characters.').format(self.max_length))

    def to_dict(self, **kwargs):
        return super().to_dict(max_length=self.max_length, **kwargs)


class RegexTextValidation(TextValidation):
    name = 'regex'

    def __init__(self, regex, **kwargs):
        self.regex = regex
        super().__init__(**kwargs)

    def validate(self, value):
        super().validate(value)
        if not bool(re.match(self.regex, value)):
            raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(regex=self.regex, **kwargs)
