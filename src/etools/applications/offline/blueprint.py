from django.utils.translation import gettext as _

from etools.applications.offline.errors import ValidationError
from etools.applications.offline.fields import Group, Structure
from etools.applications.offline.metadata import Metadata


class Blueprint:
    def __init__(
        self, code: str, title: str,
        offline_enabled=True, allow_multiple_responses=True,
        **kwargs
    ):
        self.code = code
        self.title = title
        self.root = Group('root', **kwargs, required=True, styling=['abstract'])
        self.metadata = Metadata(
            offline_enabled=offline_enabled,
            allow_multiple_responses=allow_multiple_responses
        )

    def add(self, *args: Structure):
        self.root.add(*args)

    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'title': self.title,
            'structure': self.root.to_dict(),
            'metadata': self.metadata.to_dict(),
        }

    def validate(self, value: dict) -> dict:
        if not value:
            raise ValidationError(_('Empty value is not allowed'))
        return self.root.validate(value, self.metadata)
