from django.core.exceptions import ImproperlyConfigured

from etools.applications.core.i18n.utils import get_default_translated, get_language_code


class TranslationFieldsMixin:
    TRANSLATIONS_FIELD = 'translations'

    def get_translated_field(self, instance, field):
        """
        Helper for getting the translated value from TRANSLATION_FIELD JSONField
        """
        code = get_language_code()

        if not hasattr(instance, field) or not hasattr(instance, self.TRANSLATIONS_FIELD):
            return None

        translations_values = getattr(instance, self.TRANSLATIONS_FIELD, {}).get(field, {})
        if code in translations_values and translations_values[code]:
            return translations_values[code]
        return getattr(instance, field)

    @staticmethod
    def get_translatable_fields(instance):
        if not instance.TRANSLATABLE_FIELDS:
            raise ImproperlyConfigured(f'TRANSLATABLE_FIELDS attribute is required for {instance.__class__.name} model')
        return instance.TRANSLATABLE_FIELDS

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for translatable in self.get_translatable_fields(instance):
            data[translatable] = self.get_translated_field(instance, translatable)
        return data

    def set_translations(self, instance):
        language = get_language_code()
        translations_values = getattr(instance, self.TRANSLATIONS_FIELD)

        for translatable in self.get_translatable_fields(instance):
            translations_values = getattr(instance, self.TRANSLATIONS_FIELD)
            if not translations_values:
                translations_values = get_default_translated(translatable)
            if translatable not in translations_values:
                translations_values.update(get_default_translated(translatable))
            translations_values[translatable][language] = getattr(instance, translatable)

        setattr(instance, self.TRANSLATIONS_FIELD, translations_values)
        instance.save(update_fields=[self.TRANSLATIONS_FIELD])

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.set_translations(instance)
        return instance

    def update(self, instance, validated_data):
        super().update(instance, validated_data)
        self.set_translations(instance)
        return instance
