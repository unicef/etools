
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework import serializers

from etools.applications.audit.serializers.risks import RiskRootSerializer


class RiskCategoriesUpdateMixin:
    """
    Mixin that allow to update risk values through engagement serializer.
    """

    def update(self, instance, validated_data):
        risk_data = {}
        for field in self.fields.values():
            if isinstance(field, RiskRootSerializer) and field.source in validated_data:
                risk_data[field.field_name] = validated_data.pop(field.source)

        instance = super().update(instance, validated_data)

        for field_name, data in risk_data.items():
            if not data:
                continue

            field = self.fields[field_name]
            category = field.get_attribute(instance)
            field.update(category, data)

        return instance


class EngagementDatesValidation:
    date_fields = [
        'partner_contacted_at',
        'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
        'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
    ]

    def validate(self, data):
        validated_data = super().validate(data)
        validated_data = self._validate_dates(validated_data)
        return validated_data

    def _validate_dates(self, validated_data):
        date_fields = self.date_fields
        errors = {}
        for key, value in validated_data.items():
            if value and key in date_fields and timezone.now().date() < value:
                errors[key] = _('Date should be in past.')

        if errors:
            raise serializers.ValidationError(errors)
        return validated_data
