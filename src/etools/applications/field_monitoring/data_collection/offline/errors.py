class ValueTypeMismatch(Exception):
    def __init__(self, value, *args):
        self.value = value
        super().__init__(*args)

    def __str__(self):
        return f'Wrong type for {self.value}'


class ValidationError(Exception):
    def __init__(self, value, *args):
        self.value = value
        super().__init__(*args)

    def __str__(self):
        return f'Invalid value: {self.value}'
