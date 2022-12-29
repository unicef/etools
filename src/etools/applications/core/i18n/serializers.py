import json

from django.conf import settings

from rest_framework.fields import CharField

from etools.applications.core.i18n.utils import get_language_code

default = settings.DEFAULT_LANGUAGE


class TranslatedChar(CharField):
    def to_internal_value(self, data):
        # Allowing basic numerics to be coerced into strings, but other types should fail.
        if isinstance(data, bool) or not isinstance(data, (str, int, float, dict)):
            self.fail('invalid')
        value = str(data)
        return value

    def to_representation(self, value):
        lang = get_language_code()
        if lang in value:
            return value[lang]

        if settings.DEFAULT_LANGUAGE in value:
            return value[settings.DEFAULT_LANGUAGE]

        value = json.dumps(value)
        value = value.encode()
        return value
