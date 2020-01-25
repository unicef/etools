from abc import ABCMeta, abstractmethod


class BaseValidation(metaclass=ABCMeta):
    validation_type = None  # todo: i guess type should be moved to inherited validations
    name = None

    @abstractmethod
    def is_valid(self, value):  # todo: how return reason? rest-like raise_exception?
        raise NotImplementedError

    def to_dict(self, **kwargs):
        data = {
            'validation_type': self.validation_type,
            'name': self.name,
        }
        data.update(kwargs)
        return data
