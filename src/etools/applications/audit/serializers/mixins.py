from django.conf import settings
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

        start_date = validated_data.get('start_date', self.instance.start_date if self.instance else None)
        end_date = validated_data.get('end_date', self.instance.end_date if self.instance else None)
        partner_contacted_at = validated_data.get('partner_contacted_at', self.instance.partner_contacted_at if self.instance else None)
        date_of_field_visit = validated_data.get('date_of_field_visit', self.instance.date_of_field_visit if self.instance else None)
        date_of_draft_report_to_ip = validated_data.get('date_of_draft_report_to_ip', self.instance.date_of_draft_report_to_ip if self.instance else None)
        date_of_comments_by_ip = validated_data.get('date_of_comments_by_ip', self.instance.date_of_comments_by_ip if self.instance else None)
        date_of_draft_report_to_unicef = validated_data.get('date_of_draft_report_to_unicef', self.instance.date_of_draft_report_to_unicef if self.instance else None)
        date_of_comments_by_unicef = validated_data.get('date_of_comments_by_unicef', self.instance.date_of_comments_by_unicef if self.instance else None)
        date_of_final_report = validated_data.get('date_of_final_report', self.instance.date_of_final_report if self.instance else None)

        if start_date and end_date and end_date < start_date:
            errors['end_date'] = _('This date should be after Period Start Date.')

        # Hotfix: partner_contacted_at validation is skipped for all Engagements update with a 'date_of_final_report' before 1 August 2024.
        if (date_of_final_report and date_of_final_report > settings.FAM_SKIP_IP_CONTACTED_VALIDATION_DATE or
                not self.instance or self.instance and not date_of_final_report):
            if end_date and partner_contacted_at and partner_contacted_at < end_date:
                errors['partner_contacted_at'] = _('This date should be after Period End Date.')

            if partner_contacted_at and date_of_field_visit and date_of_field_visit < partner_contacted_at:
                errors['date_of_field_visit'] = _('This date should be after Date IP was contacted.')

            if date_of_field_visit and date_of_draft_report_to_ip and date_of_draft_report_to_ip < date_of_field_visit:
                # date of field visit is editable even if date of draft report is readonly, map error to field visit date
                errors['date_of_field_visit'] = _('This date should be before Date Draft Report Issued to IP.')
            if date_of_draft_report_to_ip and date_of_comments_by_ip and date_of_comments_by_ip < date_of_draft_report_to_ip:
                errors['date_of_comments_by_ip'] = _('This date should be after Date Draft Report Issued to UNICEF.')
            if date_of_comments_by_ip and date_of_draft_report_to_unicef and date_of_draft_report_to_unicef < date_of_comments_by_ip:
                errors['date_of_draft_report_to_unicef'] = _('This date should be after Date Comments Received from IP.')
            if date_of_draft_report_to_unicef and date_of_comments_by_unicef and date_of_comments_by_unicef < date_of_draft_report_to_unicef:
                errors['date_of_comments_by_unicef'] = _('This date should be after Date Draft Report Issued to UNICEF.')

        if errors:
            raise serializers.ValidationError(errors)
        return validated_data
