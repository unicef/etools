from typing import Any

from django.core.exceptions import ImproperlyConfigured

from etools.applications.offline.errors import BadValueError
from etools.applications.offline.fields.base import BaseField
from etools.applications.offline.metadata import Metadata


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
        choices = metadata.options[self.options_key]
        options_type = choices['options_type']
        if options_type == 'local_flat':
            values = choices['values']
        elif options_type == 'local_pairs':
            values = choices['values'].values()
        elif options_type == 'remote':
            raise NotImplementedError
        else:
            raise ImproperlyConfigured(f'Unknown options type: {options_type}')

        if value not in values:
            raise BadValueError(value)

        return value
