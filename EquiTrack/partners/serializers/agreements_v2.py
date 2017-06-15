
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.db import transaction

from partners.serializers.partner_organization_v2 import PartnerStaffMemberNestedSerializer, SimpleStaffMemberSerializer
from users.serializers import SimpleUserSerializer
from partners.validation.agreements import AgreementValid
from partners.models import (
    Agreement,
    AgreementAmendment,
    AgreementAmendmentType,
)
from reports.models import CountryProgramme


class AgreementAmendmentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AgreementAmendmentType
        fields = "__all__"


class AgreementAmendmentCreateUpdateSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    amendment_types = AgreementAmendmentTypeSerializer(many=True, read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)

    class Meta:
        model = AgreementAmendment
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        amd_types = self.context.pop('amendment_types', [])
        if not amd_types:
            raise ValidationError('Agreement Amendment needs a type')

        instance = super(AgreementAmendmentCreateUpdateSerializer, self).create(validated_data)

        for a in amd_types:
            a["agreement_amendment"] = instance.pk

            agr_amd_type_serializer = AgreementAmendmentTypeSerializer(data=a)
            if agr_amd_type_serializer.is_valid(raise_exception=True):
                agr_amd_type_serializer.save()

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        amd_types = self.context.pop('amendment_types', [])

        for a in amd_types:
            a["agreement_amendment"] = instance.pk
            if a.get('id'):
                try:
                    agr_amd_type = AgreementAmendmentType.objects.get(id=a['id'])
                    agr_amd_type_serializer = AgreementAmendmentTypeSerializer(instance=agr_amd_type,
                                                                               data=a,
                                                                               partial=True)
                except AgreementAmendmentType.DoesNotExist:
                    raise ValidationError('Agreement Amendment Type received an id that is not present in the db {}'.
                                          format(a['id']))
            else:
                agr_amd_type_serializer = AgreementAmendmentTypeSerializer(data=a)

            if agr_amd_type_serializer.is_valid(raise_exception=True):
                agr_amd_type_serializer.save()

        return super(AgreementAmendmentCreateUpdateSerializer, self).update(instance, validated_data)


class AgreementListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
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
        return ', '.join([sm.get_full_name() for sm in obj.authorized_officers.all()])

    def get_amendments(self, obj):
        return ', '.join(['{} ({})'.format(am.number, am.signed_date) for am in obj.amendments.all()])

    def get_url(self, obj):
        return 'https://{}/pmp/agreements/{}/details/'.format(self.context['request'].get_host(), obj.id)


class AgreementRetrieveSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    authorized_officers = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    amendments = AgreementAmendmentCreateUpdateSerializer(many=True, read_only=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by')
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager')
    attached_agreement_file = serializers.FileField(source="attached_agreement", read_only=True)

    class Meta:
        model = Agreement
        fields = "__all__"


class AgreementCreateUpdateSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    amendments = AgreementAmendmentCreateUpdateSerializer(many=True, read_only=True)
    country_programme = serializers.PrimaryKeyRelatedField(queryset=CountryProgramme.objects.all(), required=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by', read_only=True)
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager', read_only=True)
    agreement_number = serializers.CharField(read_only=True)
    attached_agreement_file = serializers.FileField(source="attached_agreement", read_only=True)

    class Meta:
        model = Agreement
        fields = "__all__"

    def validate(self, data):
        data = super(AgreementCreateUpdateSerializer, self).validate(data)

        # When running validations in the serializer.. keep in mind that the
        # related fields have not been updated and therefore not accessible on old_instance.relatedfield_old.
        # If you want to run validation only after related fields have been updated. please run it in the view
        if self.context.get('skip_global_validator', None):
            return data
        validator = AgreementValid(data, old=self.instance, user=self.context['request'].user)

        if not validator.is_valid:
            raise serializers.ValidationError({'errors': validator.errors})
        return data
