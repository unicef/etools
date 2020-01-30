from etools.applications.offline.metadata import Metadata
from etools.applications.offline.structure import Group, Structure


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

    def to_dict(self):
        return {
            'blueprint_type': self.blueprint_type,
            'title': self.title,
            'structure': self.root.to_dict(),
            'metadata': self.metadata.to_dict(),
        }

    def validate(self, value: any):
        self.root.validate(value, self.metadata)
