
from rest_framework import serializers

from partners.serializers.partner_organization_v2 import PartnerStaffMemberNestedSerializer, SimpleStaffMemberSerializer
from users.serializers import SimpleUserSerializer
from partners.validation.agreements import AgreementValid
from partners.models import (
    Agreement,
    AgreementAmendment,
    AgreementAmendmentType,
)


class AgreementAmendmentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AgreementAmendmentType
        fields = "__all__"


class AgreementAmendmentCreateUpdateSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    amendment_types = AgreementAmendmentTypeSerializer(many=True)

    class Meta:
        model = AgreementAmendment
        fields = "__all__"

    def update(self, instance, validated_data):
        amd_types = validated_data.pop('amendment_types')
        print validated_data
        instance = AgreementAmendment.objects.update(**validated_data)
        print amd_types
        instance.amendment_types.delete()
        for amd_type in amd_types:
            AgreementAmendmentType.objects.create(**amd_type)

        instance.save()
        return instance


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
            "amendments"
        )

    def get_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.authorized_officers.all()])

    def get_amendments(self, obj):
        return ', '.join(['{} ({}/{})'.format(am.number, am.signed_date, am.type) for am in obj.amendments.all()])


class AgreementRetrieveSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    authorized_officers = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    amendments = AgreementAmendmentCreateUpdateSerializer(many=True, read_only=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by')
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager')

    class Meta:
        model = Agreement
        fields = "__all__"


class AgreementCreateUpdateSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    amendments = AgreementAmendmentCreateUpdateSerializer(many=True)
    unicef_signatory = SimpleUserSerializer(source='signed_by', read_only=True)
    partner_signatory = SimpleStaffMemberSerializer(source='partner_manager', read_only=True)
    agreement_number = serializers.CharField(read_only=True)

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
