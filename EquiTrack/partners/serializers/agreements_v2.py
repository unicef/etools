import json
from operator import xor

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from partners.serializers.v1 import (
    PartnerOrganizationSerializer,
    PartnerStaffMemberEmbedSerializer,
    InterventionSerializer,
)
from locations.models import Location

from users.serializers import SimpleProfileSerializer

from .v1 import PartnerStaffMemberSerializer

from partners.models import (
    PCA,
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    Agreement,
    PartnerStaffMember,

)


class AgreementListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    signed_by = SimpleProfileSerializer()

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
            "reference_number",
            "partner_name",
            "agreement_type",
            "end",
            "start",
            "signed_by_unicef_date",
            "signed_by_partner_date",
            "status",
            "signed_by",
        )


class AgreementExportSerializer(serializers.ModelSerializer):

    staff_members = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_manager_name = serializers.CharField(source='partner_manager.get_full_name')
    signed_by_name = serializers.CharField(source='signed_by.get_full_name')

    class Meta:
        model = Agreement
        fields = (
            "reference_number",
            "status",
            "partner_name",
            "agreement_type",
            "start",
            "end",
            "partner_manager_name",
            "signed_by_partner_date",
            "signed_by_name",
            "signed_by_unicef_date",
            "staff_members",
        )

    def get_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.authorized_officers.all()])


class AgreementRetrieveSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    authorized_officers = PartnerStaffMemberEmbedSerializer(many=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
            "authorized_officers",
            "partner_name",
            "agreement_type",
            "agreement_number",
            "attached_agreement",
            "start",
            "end",
            "signed_by_unicef_date",
            "signed_by",
            "signed_by_partner_date",
            "partner_manager",
            "status",
            "year",
            "reference_number",
        )


class AgreementCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement
        fields = "__all__"

    def validate(self, data):
        data = super(AgreementCreateUpdateSerializer, self).validate(data)
        errors = {}

        start_errors = []
        if data.get("end", None) and not data.get("start", None):
            start_errors.append("Start date must be provided along with end date.")
        if data.get("start", None) != max(data.get("signed_by_unicef_date", None), data.get("signed_by_partner_date", None)):
            start_errors.append("Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).")
        if start_errors:
            errors.update(start=start_errors)

        if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
            errors.update(partner_manager=["partner_manager and signed_by_partner_date must be provided."])
            errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager must be provided."])

        if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("signed_by", None))):
            errors.update(signed_by=["signed_by and signed_by_unicef_date must be provided."])
            errors.update(signed_by_unicef_date=["signed_by_unicef_date and signed_by must be provided."])

        if data.get("agreement_type", None) in [Agreement.PCA, Agreement.SSFA] and data.get("partner", None):
            partner = data.get("partner", None)
            if not partner.partner_type == "Civil Society Organization":
                errors.update(partner=["Partner type must be CSO for PCA or SSFA agreement types."])

        if errors:
            raise serializers.ValidationError(errors)
        return data

