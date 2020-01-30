from etools.applications.offline.errors import MissingRequiredValueError, ValidationError, ValueTypeMismatch
from etools.applications.offline.metadata import Metadata


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
