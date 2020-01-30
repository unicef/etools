from etools.applications.field_monitoring.data_collection.offline.errors import ValidationError, ValueTypeMismatch
from etools.applications.field_monitoring.data_collection.offline.metadata import Metadata


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
    def __init__(self, required=False, repeatable=False, **kwargs):
        self.repeatable = repeatable
        self.required = required
        super().__init__(**kwargs)

    def to_dict(self, **kwargs):
        return super().to_dict(repeatable=self.repeatable, required=self.required, **kwargs)

    def validate_single_value(self, value: any, metadata: Metadata):
        raise NotImplementedError

    def validate(self, value: any, metadata: Metadata):
        if not value:
            if self.required:
                raise ValidationError(value)
            else:
                return

        if self.repeatable:
            if not isinstance(value, list):
                raise ValueTypeMismatch(value)
            for v in value:
                self.validate_single_value(v, metadata)
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
        self.name = name
        self.input_type = input_type
        self.label = label or name
        self.validations = validations or []
        self.help_text = help_text
        self.placeholder = placeholder
        self.default_value = default_value
        self.options_key = options_key
        super().__init__(**kwargs)

    def to_dict(self, **kwargs):
        return super().to_dict(
            name=self.name,
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
        validators = [metadata.validations[v] for v in self.validations]
        if not all(validator.is_valid(value) for validator in validators):
            raise ValidationError(value)  # todo: we need to collect errors here


class Group(ValidatedStructure):
    object_type = 'group'

    def __init__(self, name: str, *children: Structure, title=None, **kwargs):
        self.name = name
        self.title = title
        self.children = list(children)
        super().__init__(**kwargs)

    def add(self, *children: Structure):
        self.children.extend(children)

    def to_dict(self, **kwargs):
        return super().to_dict(
            title=self.title,
            name=self.name,
            children=[c.to_dict() for c in self.children],
            **kwargs
        )

    def validate_single_value(self, value: any, metadata: Metadata):
        if not isinstance(value, dict):
            raise ValueTypeMismatch(value)

        for child in self.children:
            child_name = getattr(child, 'name', None)  # todo: name should be in structure
            if not child_name:
                continue

            if hasattr(child, 'validate'):
                child.validate(value.get(child_name), metadata)


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
