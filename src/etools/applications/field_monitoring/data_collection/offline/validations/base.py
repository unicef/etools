from abc import ABCMeta, abstractmethod


class BaseValidation(metaclass=ABCMeta):
    validation_type = None  # todo: i guess type should be moved to inherited validations
    name = None

    def __init__(self, required=False, **kwargs):
        self.required = required

    @abstractmethod
    def is_valid(self, value):  # todo: how return reason? rest-like raise_exception?
        raise NotImplementedError

    def to_dict(self, **kwargs):
        data = {
            'validation_type': self.validation_type,
            'name': self.name,
            'required': self.required
        }
        data.update(kwargs)
        return data
