from django.utils.encoding import force_text

from attachments.serializers_fields import ModelChoiceField


class ModelChoiceFieldMixin(object):
    """
    Mixin for displaying field choices based on model data.
    """
    def get_field_info(self, field):
        field_info = super(ModelChoiceFieldMixin, self).get_field_info(field)
        if (not field_info.get('read_only') and
                isinstance(field, ModelChoiceField) and hasattr(field, 'choices')):
            field_info['choices'] = [
                {
                    'value': choice_value,
                    'display_name': force_text(choice_name, strings_only=True)
                }
                for choice_value, choice_name in field.choices.items()
            ]
        return field_info
