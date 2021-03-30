from etools.applications.offline.fields.base import Structure


class Information(Structure):
    object_type = 'information'

    def __init__(self, text='', **kwargs):
        self.text = text
        super().__init__(**kwargs)

    def to_dict(self, **kwargs) -> dict:
        return super().to_dict(
            text=self.text,
            **kwargs
        )
