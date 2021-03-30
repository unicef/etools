from etools.applications.offline.errors import ValidationError, ValueTypeMismatch
from etools.applications.offline.fields.base import SkipField, Structure, ValidatedStructure
from etools.applications.offline.metadata import Metadata


class Group(ValidatedStructure):
    object_type = 'group'

    def __init__(self, name: str, *children: Structure, title=None, **kwargs):
        super().__init__(name, **kwargs)
        self.title = title
        self.children = list(children)

    def add(self, *children: Structure):
        self.children.extend(children)

    def to_dict(self, **kwargs) -> dict:
        return super().to_dict(
            title=self.title,
            children=[c.to_dict() for c in self.children],
            **kwargs
        )

    def validate_single_value(self, value: dict, metadata: Metadata) -> dict:
        if not isinstance(value, dict):
            raise ValueTypeMismatch(value)

        # preprocess value, because keys can be used as numbers, so we we'll be unable to find child value by str name
        value = {
            str(key): value for key, value in value.items()
        }

        errors = {}
        for child in self.children:
            if not isinstance(child, ValidatedStructure):
                continue

            try:
                value[child.name] = child.validate(value.get(child.name), metadata)
            except ValidationError as ex:
                errors[child.name] = ex.detail
            except SkipField:
                continue

        if errors:
            raise ValidationError(errors)
        return value
