from django.conf import settings
from django.utils import translation


def get_default_translated(*fields):
    return {
        field: {lang_code: '' for lang_code, _ in settings.LANGUAGES} for field in fields
    }


def get_language_code():
    code = settings.DEFAULT_LANGUAGE
    try:
        lang = translation.get_language_info(translation.get_language())
    except TypeError:
        return code
    for language_code in settings.LANGUAGES:
        if language_code[0] == lang['code']:
            return language_code[0]
    return code
