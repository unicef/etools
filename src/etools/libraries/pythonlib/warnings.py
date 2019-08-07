import warnings


class DeprecatedAPIClass:
    def __init__(self, *args, **kwargs):
        warnings.warn('This class has been deprecate, please update to use next version', Warning, stacklevel=3)
        super().__init__(*args, **kwargs)
