from __future__ import unicode_literals

from rest_framework import serializers

from partners.serializers.fields import TypeArrayField
from partners.models import (
    Agreement,
    AgreementAmendment,
)


class AgreementAmendmentExportSerializer(serializers.ModelSerializer):
    agreement_number = serializers.CharField(
        source="agreement.agreement_number",
        read_only=True
    )
    types = TypeArrayField()

    class Meta:
        model = AgreementAmendment
        fields = (
            "number",
            "agreement_number",
            "signed_amendment",
            "types",
            "signed_date",
        )


class AgreementAmendmentExportFlatSerializer(AgreementAmendmentExportSerializer):
    signed_amendment_file = serializers.FileField(
        source="signed_amendment",
        read_only=True
    )

    class Meta:
        model = AgreementAmendment
        fields = (
            "id",
            "number",
            "agreement_number",
            "signed_amendment_file",
            "types",
            "signed_date",
            "created",
            "modified",
        )


class AgreementExportSerializer(serializers.ModelSerializer):
    staff_members = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_manager_name = serializers.CharField(source='partner_manager.get_full_name')
    signed_by_name = serializers.CharField(source='signed_by.get_full_name')
    amendments = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = (
            "agreement_number",
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
            "amendments",
            "url",
        )

    def get_staff_members(self, obj):
        return ', '.join(
            [sm.get_full_name() for sm in obj.authorized_officers.all()]
        )

    def get_amendments(self, obj):
        return ', '.join(
            ['{} ({})'.format(am.number, am.signed_date)
             for am in obj.amendments.all()]
        )

    def get_url(self, obj):
        return 'https://{}/pmp/agreements/{}/details/'.format(
            self.context['request'].get_host(),
            obj.pk
        )


class AgreementExportFlatSerializer(AgreementExportSerializer):
    attached_agreement_file = serializers.FileField(
        source="attached_agreement",
        read_only=True
    )
    country_programme_name = serializers.CharField(
        source='country_programme.name',
        read_only=True
    )

    class Meta:
        model = Agreement
        fields = (
            "id",
            "agreement_number",
            "attached_agreement_file",
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
            "amendments",
            "country_programme_name",
            "created",
            "modified",
        )
