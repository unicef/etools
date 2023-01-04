from django.conf import settings
from django.utils import translation


def get_default_translated():
    return {lang_code: '' for lang_code, _ in settings.LANGUAGES}


def get_language_code():
    code = settings.LANGUAGE_CODE
    try:
        lang = translation.get_language_info(translation.get_language())
    except TypeError:
        return code
    for language_code in settings.LANGUAGES:
        if language_code[0] == lang['code']:
            return language_code[0]
    return code


def get_languages():
    return {lang[0]: lang[1] for lang in settings.LANGUAGES}


def get_translated_field(obj, field):
    """
    Helper for getting the translated value from a TranslatedTextField
    """
    code = get_language_code()

    if not hasattr(obj, field):
        return None

    field_value = getattr(obj, field, {})

    from etools.applications.core.i18n.fields import TranslatedText
    if isinstance(field_value, TranslatedText):
        return str(field_value)

    if code in field_value:
        return field_value[code] if field_value[code] else field_value[settings.LANGUAGE_CODE]
    return field_value
