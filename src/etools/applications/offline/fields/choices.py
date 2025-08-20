from typing import Any, List, Set, Tuple

from django.core.exceptions import ImproperlyConfigured

from etools.applications.offline.errors import BadValueError
from etools.applications.offline.fields.base import BaseField
from etools.applications.offline.metadata import Metadata


class Options:
    options_type = None

    def get_options(self):
        raise NotImplementedError

    def get_keys(self):
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            'options_type': self.options_type,
            'values': self.get_options()
        }


class LocalOptions(Options):
    """
    Flat static or almost static options
    """

    def __init__(self, options: Any):
        self.options = options

    def get_options(self) -> Any:
        return self.options


class LocalFlatOptions(LocalOptions):
    """
    option = 1
    """

    options_type = 'local_flat'

    def get_keys(self) -> Set:
        return set(self.get_options())


class LocalPairsOptions(LocalOptions):
    """
    option = {'value': 1, 'label': 'One"}
    """

    options_type = 'local_pairs'

    def __init__(self, options: [List, Tuple]):
        if options and isinstance(options[0], (list, tuple)):
            options = [
                {'value': option[0], 'label': option[1]}
                for option in options
            ]
        super().__init__(options)

    def get_keys(self) -> Set:
        return set(c['value'] for c in self.get_options())


class RemoteOptions(Options):
    """
    options are dynamic and should be fetched in time. frontend can fetch them by url with optional auth
    """

    options_type = 'remote'

    def __init__(self, url: str, auth_required=False):
        self.url = url
        self.auth_required = auth_required
        super().__init__()


class ChoiceField(BaseField):
    input_type = 'likert_scale'

    """
    todo: not sure how we can check types here.
    1: we can subclass it from another fields. there possibly can be lot of combinations (not bad if made in place)
    2. we can ask value type in constructor
    3. should we check type at all? we validate it by checking value is in choices, so types are implicitly checked
        ! but not when options_type = remote
    4. what we should do when choices are remote? should we validate? maybe make abstract get_choices?
        can we face to the totally remote choices? it may be some problems with authentication
    """

    def __init__(self, name: str, **kwargs):
        if not kwargs.get('options_key'):
            raise ImproperlyConfigured('options key is required for choice field')
        super().__init__(name, self.input_type, **kwargs)

    def validate_single_value(self, value: Any, metadata: Metadata) -> Any:
        value = super().validate_single_value(value, metadata)
        keys = metadata.options[self.options_key].get_keys()
        if value not in keys:
            raise BadValueError(value)

        return value


class MultiChoiceField(BaseField):
    input_type = 'multiple_choice'

    def __init__(self, name: str, **kwargs):
        if not kwargs.get('options_key'):
            raise ImproperlyConfigured('options key is required for multi choice field')
        super().__init__(name, self.input_type, **kwargs)

    def validate_single_value(self, value: Any, metadata: Metadata) -> Any:
        value = super().validate_single_value(value, metadata)
        keys = metadata.options[self.options_key].get_keys()

        if not isinstance(value, (list, tuple)):
            raise BadValueError(f"Expected a list or tuple of choices, got {type(value).__name__}")

        invalid_values = [v for v in value if v not in keys]
        if invalid_values:
            raise BadValueError(f"Invalid choices: {invalid_values}")

        return value
