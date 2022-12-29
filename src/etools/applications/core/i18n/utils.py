from django.conf import settings
from django.utils import translation

from etools.applications.core.i18n.serializers import TranslatedChar


def get_default_field_value():
    return {lang_code: '' for lang_code, _ in settings.LANGUAGES}


def get_language_code():
    code = settings.DEFAULT_LANGUAGE
    try:
        lang = translation.get_language_info(translation.get_language())
    except TypeError:
        return code
    for lng in settings.LANGUAGES:
        if lng[0] == lang['code']:
            code = lng[0]
    return code


def get_languages():
    return {lang[0]: lang[1] for lang in settings.LANGUAGES}
