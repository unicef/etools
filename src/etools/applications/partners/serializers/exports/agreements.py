from django.utils.translation import gettext as _

from rest_framework import serializers

from etools.applications.core.mixins import ExportSerializerMixin
from etools.applications.partners.models import Agreement, AgreementAmendment
from etools.applications.partners.serializers.fields import TypeArrayField


class AgreementAmendmentExportSerializer(serializers.ModelSerializer):
    agreement_number = serializers.CharField(
        source="agreement.agreement_number",
        read_only=True
    )
    types = TypeArrayField()

    class Meta:
        model = AgreementAmendment
        fields = "__all__"


class AgreementAmendmentExportFlatSerializer(AgreementAmendmentExportSerializer):
    signed_amendment_file = serializers.FileField(
        source="signed_amendment",
        read_only=True
    )


class AgreementExportSerializer(serializers.ModelSerializer):
    staff_members = serializers.SerializerMethodField(
        label=_("Partner Authorized Officer"),
    )
    partner_name = serializers.CharField(
        label="Partner Name",
        source='partner.name',
        read_only=True,
    )
    partner_number = serializers.CharField(
        label="Partner Number",
        source='partner.vendor_number',
        read_only=True,
    )
    partner_manager_name = serializers.CharField(
        label=_("Signed By Partner"),
        source='partner_manager.get_full_name',
        read_only=True,
        allow_null=True,
    )
    signed_by_name = serializers.CharField(
        label=_("Signed By UNICEF"),
        source='signed_by.get_full_name',
        read_only=True,
    )
    amendments = serializers.SerializerMethodField(label=_("Amendments"))
    url = serializers.SerializerMethodField(label=_("URL"))
    special_conditions_pca = serializers.SerializerMethodField(
        label=_("Special Conditions PCA"),
    )
    terms_acknowledged_by = serializers.CharField(
        label=_("Terms Acknowledged By"),
        source='terms_acknowledged_by.get_full_name',
        read_only=True,
    )

    class Meta:
        model = Agreement
        fields = (
            "agreement_number",
            "status",
            "partner_name",
            "partner_number",
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
            "special_conditions_pca",
            "terms_acknowledged_by",
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

    def get_special_conditions_pca(self, obj):
        return "Yes" if obj.special_conditions_pca else "No"


class AgreementExportFlatSerializer(ExportSerializerMixin, AgreementExportSerializer):
    attached_agreement_file = serializers.FileField(
        label=_("Attached Agreement"),
        source="attached_agreement",
        read_only=True
    )
    country_programme_name = serializers.CharField(
        label=_("Country Programme"),
        source='country_programme.name',
        read_only=True
    )

    class Meta:
        model = Agreement
        fields = "__all__"
