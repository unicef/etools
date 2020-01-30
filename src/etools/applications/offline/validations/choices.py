from etools.applications.offline.errors import BadValueError
from etools.applications.offline.validations.base import BaseValidation


class Choice:
    def __init__(self, code, label=None):
        self.code = code
        self.label = label or self.code

    def to_dict(self):
        return {'code': self.code, 'label': self.label}


class ChoicesValidation(BaseValidation):
    validation_type = 'choices'
    name = 'choices'

    def __init__(self, choices=None, **kwargs):
        self.choices = choices or []
        super().__init__(**kwargs)

    def get_choices(self):
        return self.choices

    def validate(self, value):
        if value not in self.get_choices():
            raise BadValueError(value)

    def to_dict(self, **kwargs):
        return super().to_dict(choices=[Choice(*c).to_dict() for c in self.get_choices()])

# todo: non-serializable remote choices validation?
