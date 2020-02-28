class ValidationError(Exception):
    def __init__(self, detail):
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]
        self.detail = detail

    def __str__(self):
        return str(self.detail)


class ValueTypeMismatch(ValidationError):
    def __init__(self, value):
        self.value = value
        super().__init__(f'Wrong type for {self.value}')


class BadValueError(ValidationError):
    def __init__(self, value):
        self.value = value
        super().__init__(f'Invalid value: {self.value}')


class MissingRequiredValueError(ValidationError):
    def __init__(self):
        super().__init__(f'This field is required')
