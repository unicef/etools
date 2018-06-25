from rest_framework import serializers
from rest_framework.serializers import ValidationError

from etools.applications.attachments.serializers_fields import AttachmentSingleFileField
from etools.applications.EquiTrack.serializers import SnapshotModelSerializer
from etools.applications.partners.models import Agreement, AgreementAmendment
from etools.applications.partners.permissions import AgreementPermissions
from etools.applications.partners.serializers.partner_organization_v2 import (PartnerStaffMemberNestedSerializer,
                                                                              SimpleStaffMemberSerializer,)
from etools.applications.partners.validation.agreements import AgreementValid
from etools.applications.reports.models import CountryProgramme
from etools.applications.users.serializers import SimpleUserSerializer


class AgreementAmendmentCreateUpdateSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)

    class Meta:
        model = AgreementAmendment
        fields = "__all__"


class AgreementAmendmentListSerializer(serializers.ModelSerializer):

    class Meta:
        model = AgreementAmendment
        fields = "__all__"


class AgreementListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
            "country_programme",
            "agreement_number",
            "partner_name",
            "agreement_type",
            "end",
            "start",
            "signed_by_unicef_date",
            "signed_by_partner_date",
            "status",
            "signed_by",
        )


class AgreementDetailSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    authorized_officers = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    amendments = AgreementAmendmentCreateUpdateSerializer(many=True, read_only=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by')
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager')
    attached_agreement_file = serializers.FileField(source="attached_agreement", read_only=True)
    attachment = AttachmentSingleFileField(read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = Agreement.permission_structure()
        permissions = AgreementPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()

    class Meta:
        model = Agreement
        fields = "__all__"


class AgreementCreateUpdateSerializer(SnapshotModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    agreement_type = serializers.CharField(required=True)
    amendments = AgreementAmendmentCreateUpdateSerializer(many=True, read_only=True)
    country_programme = serializers.PrimaryKeyRelatedField(queryset=CountryProgramme.objects.all(), required=False,
                                                           allow_null=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by', read_only=True)
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager', read_only=True)
    agreement_number = serializers.CharField(read_only=True)
    attached_agreement_file = serializers.FileField(source="attached_agreement", read_only=True)
    attachment = AttachmentSingleFileField(read_only=True)

    class Meta:
        model = Agreement
        fields = "__all__"

    def validate(self, data):
        data = super(AgreementCreateUpdateSerializer, self).validate(data)
        agreement_type = data.get('agreement_type', None) or self.instance.agreement_type

        if agreement_type == Agreement.PCA:
            # Look for country programme in data and on instance.
            country_programme = data.get('country_programme')
            if not country_programme and self.instance:
                country_programme = self.instance.country_programme

            if country_programme is None:
                raise ValidationError({'country_programme': 'Country Programme is required for PCAs!'})

        # When running validations in the serializer.. keep in mind that the
        # related fields have not been updated and therefore not accessible on old_instance.relatedfield_old.
        # If you want to run validation only after related fields have been updated. please run it in the view
        if self.context.get('skip_global_validator', None):
            return data
        validator = AgreementValid(data, old=self.instance, user=self.context['request'].user)

        if not validator.is_valid:
            raise serializers.ValidationError({'errors': validator.errors})
        return data
