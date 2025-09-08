from django.utils.translation import gettext as _

from rest_framework import serializers

from etools.applications.audit.models import Audit, SpotCheck
from etools.applications.audit.serializers.export import (
    AuditDetailCSVSerializer,
    AuditPDFSerializer,
    CurrencyReadOnlyField,
    EngagementBaseDetailCSVSerializer,
    SpotCheckDetailCSVSerializer,
    SpotCheckPDFSerializer,
)


class FaceAuditPDFSerializer(AuditPDFSerializer):

    class Meta(AuditPDFSerializer.Meta):
        model = Audit
        fields = AuditPDFSerializer.Meta.fields + [
            'amount_refunded_local',
            'additional_supporting_documentation_provided_local',
            'justification_provided_and_accepted_local',
            'write_off_required_local',
            'pending_unsupported_amount_local',
            'total_value_local',
        ]


class FaceSpotCheckPDFSerializer(SpotCheckPDFSerializer):
    percent_of_audited_expenditure = serializers.DecimalField(20, 2, label=_('% of Audited Expenditure'), read_only=True)

    class Meta(SpotCheckPDFSerializer.Meta):
        model = SpotCheck
        fields = SpotCheckPDFSerializer.Meta.fields + [
            'total_amount_tested_local',
            'total_amount_of_ineligible_expenditure_local',
            'amount_refunded_local',
            'additional_supporting_documentation_provided_local',
            'justification_provided_and_accepted_local',
            'write_off_required_local',
            'pending_unsupported_amount_local',
            'total_value_local',
            'percent_of_audited_expenditure'
        ]


class FaceSpotCheckDetailCSVSerializer(SpotCheckDetailCSVSerializer):
    amount_refunded_local = CurrencyReadOnlyField()
    additional_supporting_documentation_provided_local = CurrencyReadOnlyField()
    justification_provided_and_accepted_local = CurrencyReadOnlyField()
    write_off_required_local = CurrencyReadOnlyField()
    pending_unsupported_amount_local = CurrencyReadOnlyField()


class FaceAuditDetailCSVSerializer(AuditDetailCSVSerializer):
    total_value_local = CurrencyReadOnlyField()
    amount_refunded_local = CurrencyReadOnlyField()
    additional_supporting_documentation_provided_local = CurrencyReadOnlyField()
    justification_provided_and_accepted_local = CurrencyReadOnlyField()
    write_off_required_local = CurrencyReadOnlyField()
    pending_unsupported_amount_local = CurrencyReadOnlyField()


class SpecialAuditDetailCSVSerializer(EngagementBaseDetailCSVSerializer):
    """

    """
