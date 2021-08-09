class BaseDetailedError(BaseException):
    def __init__(self, code, description, extra=None):
        super().__init__(self)
        self.code = code
        self.description = description
        self.extra = extra or {}

    def __str__(self):
        return self.description

    @property
    def details(self):
        return {
            'code': self.code,
            'description': self.description,
            'extra': self.extra,
        }


class DetailedBasicValidationError(BaseDetailedError):
    pass


class DetailedTransitionError(BaseDetailedError):
    pass


class DetailedStateValidationError(BaseDetailedError):
    pass
