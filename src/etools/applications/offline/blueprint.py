from etools.applications.offline.fields import Group, Structure
from etools.applications.offline.metadata import Metadata


class Blueprint:
    def __init__(
        self, blueprint_type: str, title: str,
        offline_enabled=True, allow_multiple_responses=True,
        **kwargs
    ):
        self.blueprint_type = blueprint_type
        self.title = title
        self.root = Group('root', **kwargs, required=True)
        self.metadata = Metadata(
            offline_enabled=offline_enabled,
            allow_multiple_responses=allow_multiple_responses
        )

    def add(self, *args: Structure):
        self.root.add(*args)

    def to_dict(self) -> dict:
        return {
            'blueprint_type': self.blueprint_type,
            'title': self.title,
            'structure': self.root.to_dict(),
            'metadata': self.metadata.to_dict(),
        }

    def validate(self, value: dict) -> dict:
        return self.root.validate(value, self.metadata)
