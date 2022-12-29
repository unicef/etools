import json
from json import JSONEncoder

from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _

from etools.applications.core.i18n.utils import get_language_code, get_languages


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder.default  # Save unmodified default.
JSONEncoder.default = _default  # Replace it.


class TranslatedText:
    value = None

    def __init__(self, value):
        if not self.value:
            self.value = {}
            for lang in get_languages():
                self.value[lang] = ''

        self.set_value(value)

    def set_value(self, value):
        lang = get_language_code()
        if isinstance(value, dict):
            self.value.update(value)
        else:
            self.value[lang] = value

    def _get_val(self):
        lang = get_language_code()
        if lang in self.value:
            return self.value[lang]
        return None

    def __str__(self):
        lang = get_language_code()
        if lang in self.value:
            return str(self.value[lang])
        return json.dumps(self.value)

    def __eq__(self, other):
        return self._get_val() == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_value(self):
        return self.value

    def to_json(self):
        return self.value


class TranslatedTextField(JSONField):
    description = _('A Translated Text field')

    def __init__(self, verbose_name=None, name=None, encoder=None, **kwargs):
        super().__init__(verbose_name, name, encoder, **kwargs)

    def deconstruct(self):
        return super().deconstruct()

    def get_prep_value(self, value):
        if not isinstance(value, TranslatedText):
            value = TranslatedText(value)

        json_value = super().get_prep_value(value.get_value())
        return json_value

    def to_python(self, value):
        if isinstance(value, TranslatedText):
            return value

        if value is None:
            return value

        return TranslatedText(value)
