from abc import ABCMeta, abstractmethod


class BaseValidation(metaclass=ABCMeta):
    name = None

    @abstractmethod
    def validate(self, value):
        raise NotImplementedError

    def to_dict(self, **kwargs):
        data = {
            'name': self.name,
        }
        data.update(kwargs)
        return data
