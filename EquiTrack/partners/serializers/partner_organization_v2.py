




class PartnerOrganizationExportSerializer(serializers.ModelSerializer):

    # pca_set = InterventionSerializer(many=True, read_only=True)
    agreement_count = serializers.SerializerMethodField()
    intervention_count = serializers.SerializerMethodField()
    active_staff_members = serializers.SerializerMethodField()

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'vision_synced', 'deleted_flag', 'blocked', 'name', 'short_name', 'alternate_id',
                  'alternate_name', 'partner_type', 'cso_type', 'shared_partner', 'address', 'email', 'phone_number',
                  'rating', 'type_of_assessment', 'last_assessment_date', 'total_ct_cp', 'total_ct_cy',
                  'agreement_count', 'intervention_count', 'active_staff_members')

    def get_agreement_count(self, obj):
        return obj.agreement_set.count()

    def get_intervention_count(self, obj):
        if obj.partner_type == PartnerType.GOVERNMENT:
            return obj.work_plans.count()
        return obj.documents.count()

    def get_active_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.staff_members.all()])


class PartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "vendor_number",
            "deleted_flag",
            "blocked",
            "name",
            "short_name",
            "partner_type",
            "rating",
            "shared_partner",
            "email",
            "phone_number",
            "total_ct_cp",
            "total_ct_cy",
        )


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        staff_members = validated_data.pop("staff_members", [])
        partner = super(PartnerOrganizationCreateUpdateSerializer, self).create(validated_data)
        for item in staff_members:
            item["partner"] = partner.id
            # Utilize extra validation logic in this serializer
            serializer = PartnerStaffMemberCreateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return partner

    @transaction.atomic
    def update(self, instance, validated_data):
        staff_members = validated_data.pop("staff_members", [])
        updated = PartnerOrganization(id=instance.id, **validated_data)
        updated.save()

        # Create or update new/changed members.
        for item in staff_members:
            item["partner"] = instance.id
            if "id" in item.keys():
                # Utilize extra validation logic in this serializer
                serializer = PartnerStaffMemberUpdateSerializer(data=item)
            else:
                # Utilize extra validation logic in this serializer
                serializer = PartnerStaffMemberCreateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return updated


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer()
    agreement_set = AgreementRetrieveSerializer(many=True)

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"