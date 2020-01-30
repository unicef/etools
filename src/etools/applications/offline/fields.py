from typing import Any

from django.core.exceptions import ImproperlyConfigured

from etools.applications.offline.errors import BadValueError, ValidationError, ValueTypeMismatch
from etools.applications.offline.metadata import Metadata
from etools.applications.offline.structure import ValidatedStructure


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

    def validate_single_value(self, value: any, metadata: Metadata):
        errors = []
        for validation in self.validations:
            validator = metadata.validations[validation]
            try:
                validator.validate(value)
            except ValidationError as ex:
                errors.extend(ex.detail)
        if errors:
            raise ValidationError(set(errors))


class BaseTypedField(BaseField):
    input_type = None
    value_type = None

    def __init__(self, name, **kwargs):
        super().__init__(name, self.input_type, **kwargs)

    def validate_single_value(self, value: any, metadata: Metadata):
        if not isinstance(value, self.value_type):
            raise ValueTypeMismatch(value)
        super().validate_single_value(value, metadata)


class TextField(BaseTypedField):
    input_type = 'text'
    value_type = str


class IntegerField(BaseTypedField):
    input_type = 'number-integer'
    value_type = int


class FloatField(BaseTypedField):
    input_type = 'number-float'
    value_type = float


class BooleanField(BaseTypedField):
    input_type = 'bool'
    value_type = bool


class FileField(TextField):
    input_type = 'file'
    # todo: do we need to validate this data at all?
    # todo: we act differently while handling files attached: not only validate, but also process and return result


class UploadedFileField(FileField):
    pass
    # todo: check attachment existence by provided id


class RemoteFileField(FileField):
    pass
    # todo: create attachment and spawn task to download the file


class ChoiceField(BaseTypedField):
    input_type = 'likert_scale'

    """
    todo: not sure how we can check types here.
    1: we can subclass it from another fields. there possibly can be lot of combinations
    2. we can ask value type in constructor
    3. should we check type at all? we validate it by checking value is in choices, so types are implicitly checked
        but not when options_type = remote
    4. what we should do when choices are remote? should we validate? maybe make abstract get_choices?
        can we face to the totally remote choices? it may be some problems with authentication
    """

    def __init__(self, name: str, value_type: Any, **kwargs):
        if 'options_key' not in kwargs:
            raise ImproperlyConfigured('options key should be provided for choice field')
        self.value_type = value_type
        super().__init__(name, **kwargs)

    def validate_single_value(self, value: Any, metadata: Metadata):
        super().validate_single_value(value, metadata)
        choices = metadata.options[self.options_key]
        options_type = choices['options_type']
        if options_type == 'local_flat':
            values = choices['values']
        elif options_type == 'local_pairs':
            values = choices['values'].values()
        elif options_type == 'remote':
            return
        else:
            raise ImproperlyConfigured(f'Unknown options type: {options_type}')

        if value not in values:
            raise BadValueError(value)
