from etools.applications.offline.errors import MissingRequiredValueError, ValueTypeMismatch, ValidationError
from etools.applications.offline.metadata import Metadata


class EmptyValue:
    pass


class Structure:
    object_type = None

    def __init__(self, extra=None):
        self.extra = extra or {}

    def to_dict(self, **kwargs):
        data = {
            'type': self.object_type,
            'extra': self.extra
        }
        data.update(kwargs)
        return data


class ValidatedStructure(Structure):
    def __init__(self, name: str, required=False, repeatable=False, **kwargs):
        self.name = name
        self.repeatable = repeatable
        self.required = required
        super().__init__(**kwargs)

    def to_dict(self, **kwargs):
        return super().to_dict(name=self.name, repeatable=self.repeatable, required=self.required, **kwargs)

    def validate_single_value(self, value: any, metadata: Metadata):
        raise NotImplementedError

    def validate(self, value: any, metadata: Metadata):
        if not value:
            if self.required:
                raise MissingRequiredValueError()
            else:
                return

        if self.repeatable:
            if not isinstance(value, list):
                raise ValueTypeMismatch(value)

            errors = [[] for i in range(len(value))]
            has_errors = False
            for i, v in enumerate(value):
                try:
                    self.validate_single_value(v, metadata)
                except ValidationError as ex:
                    has_errors = True
                    errors[i] = ex.detail

            if has_errors:
                raise ValidationError(errors)
        else:
            self.validate_single_value(value, metadata)


class Field(ValidatedStructure):
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
        # default_value=EmptyValue,  # todo; specific logic may be required for different fields
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
            label=str(self.label),  # todo: make universal solution for translated strings
            validations=self.validations,
            help_text=self.help_text,
            placeholder=self.placeholder,
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


class Group(ValidatedStructure):
    object_type = 'group'

    def __init__(self, name: str, *children: Structure, title=None, **kwargs):
        super().__init__(name, **kwargs)
        self.title = title
        self.children = list(children)

    def add(self, *children: Structure):
        self.children.extend(children)

    def to_dict(self, **kwargs):
        return super().to_dict(
            title=self.title,
            children=[c.to_dict() for c in self.children],
            **kwargs
        )

    def validate_single_value(self, value: any, metadata: Metadata):
        if not isinstance(value, dict):
            raise ValueTypeMismatch(value)

        errors = {}
        for child in self.children:
            if not isinstance(child, ValidatedStructure):
                continue

            try:
                child.validate(value.get(child.name), metadata)
            except ValidationError as ex:
                errors[child.name] = ex.detail

        if errors:
            raise ValidationError(errors)


class Information(Structure):
    object_type = 'information'

    def __init__(self, text='', **kwargs):
        self.text = text
        super().__init__(**kwargs)

    def to_dict(self, **kwargs):
        return super().to_dict(
            text=self.text,
            **kwargs
        )
