from operator import xor

from rest_framework import serializers

from partners.models import Agreement, PartnerOrganization


class AgreementListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "reference_number",
            "partner_name",
            "agreement_type",
            "end",
            "start",
            "signed_by_unicef_date",
            "signed_by_partner_date",
            "status",
            "partner_manager",
            "signed_by",
            "attached_agreement",
        )


class AgreementSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
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
            "bank_name",
            "bank_address",
            "account_title",
            "account_number",
            "routing_details",
            "bank_contact_person",
            "year",
            "reference_number",
        )

    def validate(self, data):
        data = super(AgreementSerializer, self).validate(data)
        errors = {}

        if data.get("end", None) and not data.get("start", None):
            errors.update(start=["Start date must be provided along with end date."])

        if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
            errors.update(partner_manager=["partner_manager and signed_by_partner_date are both must be provided."])
            errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager are both must be provided."])

        if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("signed_by", None))):
            errors.update(signed_by=["signed_by and signed_by_unicef_date are both must be provided."])
            errors.update(signed_by_unicef_date=["signed_by_unicef_date and signed_by are both must be provided."])

        if data.get("agreement_type", None) in [Agreement.PCA, Agreement.SSFA] and data.get("partner", None):
            partner = data.get("partner", None)
            if not partner.partner_type == "Civil Society Organization":
                errors.update(partner=["Partner type must be CSO for PCA or SSFA agreement types."])

        if errors:
            raise serializers.ValidationError(errors)
        return data
