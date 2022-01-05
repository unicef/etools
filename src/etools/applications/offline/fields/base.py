from typing import Any

from etools.applications.offline.errors import MissingRequiredValueError, ValidationError, ValueTypeMismatch
from etools.applications.offline.metadata import Metadata


class Structure:
    object_type = None

    def __init__(self, styling=None, extra=None):
        self.styling = styling or []
        self.extra = extra or {}

    def to_dict(self, **kwargs) -> dict:
        data = {
            'type': self.object_type,
            'extra': self.extra,
            'styling': self.styling,
        }
        data.update(kwargs)
        return data


class SkipField(Exception):
    pass


class ValidatedStructure(Structure):
    def __init__(self, name: str, required=True, repeatable=False, **kwargs):
        self.name = name
        self.repeatable = repeatable
        self.required = required
        super().__init__(**kwargs)

    def to_dict(self, **kwargs) -> dict:
        return super().to_dict(name=self.name, repeatable=self.repeatable, required=self.required, **kwargs)

    def validate_single_value(self, value: any, metadata: Metadata) -> Any:
        return value

    def validate(self, value: any, metadata: Metadata) -> Any:
        if value is None:  # todo: default should be checked here; None is the value too
            if self.required:
                raise MissingRequiredValueError()
            else:
                raise SkipField

        if self.repeatable:
            if not isinstance(value, list):
                raise ValueTypeMismatch(value)

            errors = [[] for i in range(len(value))]
            has_errors = False
            for i, v in enumerate(value):
                try:
                    value[i] = self.validate_single_value(v, metadata)
                except ValidationError as ex:
                    has_errors = True
                    errors[i] = ex.detail

            if has_errors:
                raise ValidationError(errors)
        else:
            value = self.validate_single_value(value, metadata)
        return value


class BaseField(ValidatedStructure):
    object_type = 'field'

    def __init__(
        self,
        name,
        input_type,
        label=None,
        validations=None,
        help_text='',
        placeholder='',
        default_value=None,
        options_key=None,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.input_type = input_type
        self.label = label or self.name
        self.validations = validations or []
        self.help_text = help_text
        self.placeholder = placeholder
        self.default_value = default_value
        self.options_key = options_key

    def to_dict(self, **kwargs):
        return super().to_dict(
            input_type=self.input_type,
            label=str(self.label),
            validations=self.validations,
            help_text=str(self.help_text),
            placeholder=str(self.placeholder),
            default_value=self.default_value,
            options_key=self.options_key,
            **kwargs
        )

    def validate_single_value(self, value: Any, metadata: Metadata) -> Any:
        errors = []
        for validation in self.validations:
            validator = metadata.validations[validation]
            try:
                validator.validate(value)
            except ValidationError as ex:
                errors.extend(ex.detail)
        if errors:
            raise ValidationError(list(set(errors)))
        return value


class BaseTypedField(BaseField):
    input_type = None

    def __init__(self, name, **kwargs):
        super().__init__(name, self.input_type, **kwargs)

    def cast_value(self, value: Any) -> Any:
        return value

    def validate_single_value(self, value: Any, metadata: Metadata) -> Any:
        return super().validate_single_value(self.cast_value(value), metadata)
