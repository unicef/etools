from django.contrib.auth import get_user_model

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField

from etools.applications.partners.models import (
    FileType,
    Intervention,
    InterventionManagementBudget,
    InterventionRisk,
    InterventionSupplyItem,
)
from etools.applications.partners.permissions import InterventionPermissions, SENIOR_MANAGEMENT_GROUP
from etools.applications.partners.serializers.interventions_v2 import (
    FRsSerializer,
    InterventionAmendmentCUSerializer,
    InterventionAttachmentSerializer,
    InterventionBudgetCUSerializer,
    InterventionResultNestedSerializer,
    PlannedVisitsNestedSerializer,
    SingleInterventionAttachmentField,
)
from etools.applications.partners.utils import get_quarters_range
from etools.applications.reports.serializers.v2 import InterventionTimeFrameSerializer


class InterventionRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionRisk
        fields = ('id', 'risk_type', 'mitigation_measures', 'intervention')
        kwargs = {'intervention': {'write_only': True}}


class InterventionSupplyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSupplyItem
        fields = (
            "id",
            "title",
            "unit_number",
            "unit_price",
            "result",
            "total_price",
            "other_mentions",
        )

    def create(self, validated_data):
        validated_data["intervention"] = self.initial_data.get("intervention")
        return super().create(validated_data)


class InterventionManagementBudgetSerializer(serializers.ModelSerializer):
    act1_total = serializers.SerializerMethodField()
    act2_total = serializers.SerializerMethodField()
    act3_total = serializers.SerializerMethodField()
    partner_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    unicef_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = InterventionManagementBudget
        fields = (
            "act1_unicef",
            "act1_partner",
            "act1_total",
            "act2_unicef",
            "act2_partner",
            "act2_total",
            "act3_unicef",
            "act3_partner",
            "act3_total",
            "partner_total",
            "unicef_total",
            "total",
        )

    def get_act1_total(self, obj):
        return str(obj.act1_unicef + obj.act1_partner)

    def get_act2_total(self, obj):
        return str(obj.act2_unicef + obj.act2_partner)

    def get_act3_total(self, obj):
        return str(obj.act3_unicef + obj.act3_partner)


class InterventionDetailSerializer(serializers.ModelSerializer):
    activation_letter_attachment = AttachmentSingleFileField(read_only=True)
    activation_letter_file = serializers.FileField(source='activation_letter', read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    available_actions = serializers.SerializerMethodField()
    status_list = serializers.SerializerMethodField()
    cluster_names = serializers.SerializerMethodField()
    days_from_review_to_signed = serializers.CharField(read_only=True)
    days_from_submission_to_signed = serializers.CharField(read_only=True)
    donor_codes = serializers.SerializerMethodField()
    donors = serializers.SerializerMethodField()
    flagged_sections = serializers.SerializerMethodField(read_only=True)
    frs_details = FRsSerializer(source='frs', read_only=True)
    grants = serializers.SerializerMethodField()
    location_names = serializers.SerializerMethodField()
    location_p_codes = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    partner = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    partner_vendor = serializers.CharField(source='agreement.partner.vendor_number')
    permissions = serializers.SerializerMethodField(read_only=True)
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    prc_review_attachment = AttachmentSingleFileField(required=False)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    section_names = serializers.SerializerMethodField(read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    submitted_to_prc = serializers.ReadOnlyField()
    termination_doc_attachment = AttachmentSingleFileField(read_only=True)
    termination_doc_file = serializers.FileField(source='termination_doc', read_only=True)
    final_partnership_review = SingleInterventionAttachmentField(
        type_name=FileType.FINAL_PARTNERSHIP_REVIEW,
        read_field=InterventionAttachmentSerializer()
    )
    risks = InterventionRiskSerializer(many=True, read_only=True)
    quarters = InterventionTimeFrameSerializer(many=True, read_only=True)
    supply_items = InterventionSupplyItemSerializer(many=True, read_only=True)
    management_budgets = InterventionManagementBudgetSerializer(read_only=True)

    def get_location_p_codes(self, obj):
        return [location.p_code for location in obj.flat_locations.all()]

    def get_donors(self, obj):
        donors = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                donors.add(fr_li.donor)
        return donors

    def get_donor_codes(self, obj):
        donor_codes = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                donor_codes.add(fr_li.donor_code)
        return donor_codes

    def get_grants(self, obj):
        grants = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                grants.add(fr_li.grant_number)
        return grants

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = Intervention.permission_structure()
        permissions = InterventionPermissions(
            user=user,
            instance=self.instance,
            permission_structure=ps,
        )
        return permissions.get_permissions()

    def get_locations(self, obj):
        return [loc.id for loc in obj.flat_locations.all()]

    def get_location_names(self, obj):
        return [
            '{} [{} - {}]'.format(
                loc.name,
                loc.gateway.name,
                loc.p_code
            ) for loc in obj.flat_locations.all()
        ]

    def get_section_names(self, obj):
        return [loc.name for loc in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [loc.id for loc in obj.sections.all()]

    def get_cluster_names(self, obj):
        return [c for c in obj.intervention_clusters()]

    def _is_management(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            groups__name__in=[SENIOR_MANAGEMENT_GROUP],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_partner_user(self, obj, user):
        return user.email in [o.email for o in obj.partner_focal_points.all()]

    def get_available_actions(self, obj):
        available_actions = [
            "download_comments",
            "export",
            "generate_pdf",
        ]
        user = self.context['request'].user

        # available actions only provided in Development status
        if obj.status != obj.DRAFT:
            return available_actions

        # PD is assigned to UNICEF
        if obj.unicef_court:
            # UNICEF User with Senior Management Team
            if self._is_management():
                available_actions.append("cancel")

            # budget owner
            if obj.budget_owner == user:
                if not obj.unicef_accepted:
                    available_actions.append("accept")
                available_actions.append("review")
                available_actions.append("signature")

            # any unicef focal point user
            if user in obj.unicef_focal_points.all():
                available_actions.append("cancel")
                if obj.unicef_court:
                    available_actions.append("send_to_partner")
                available_actions.append("signature")
                if obj.partner_accepted:
                    available_actions.append("unlock")
                else:
                    available_actions.append("accept")
                    # TODO confirm that this is focal point
                    # and not just any UNICEF user
                    available_actions.append("accept_review")

        # PD is assigned to Partner
        else:
            # any partner focal point user
            if self._is_partner_user(obj, user):
                if not obj.unicef_court:
                    available_actions.append("send_to_unicef")
                if obj.partner_accepted:
                    available_actions.append("unlock")
                else:
                    available_actions.append("accept")

        return list(set(available_actions))

    def get_status_list(self, obj):
        if obj.status == obj.SUSPENDED:
            status_list = [
                obj.DRAFT,
                obj.REVIEW,
                obj.SIGNATURE,
                obj.SIGNED,
                obj.SUSPENDED,
                obj.ACTIVE,
                obj.ENDED,
            ]
        elif obj.status == obj.TERMINATED:
            status_list = [
                obj.DRAFT,
                obj.REVIEW,
                obj.SIGNATURE,
                obj.SIGNED,
                obj.TERMINATED,
            ]
        else:
            status_list = [
                obj.DRAFT,
                obj.REVIEW,
                obj.SIGNATURE,
                obj.SIGNED,
                obj.ACTIVE,
                obj.ENDED,
            ]
        return [s for s in obj.INTERVENTION_STATUS if s[0] in status_list]

    def get_quarters(self, obj: Intervention):
        return [
            {
                'name': 'Q{}'.format(i + 1),
                'start': quarter[0].strftime('%Y-%m-%d'),
                'end': quarter[1].strftime('%Y-%m-%d')
            }
            for i, quarter in enumerate(get_quarters_range(obj.start, obj.end))
        ]

    class Meta:
        model = Intervention
        fields = (
            "activation_letter_attachment",
            "activation_letter_file",
            "agreement",
            "amendments",
            "attachments",
            "available_actions",
            "budget_owner",
            "capacity_development",
            "cash_transfer_modalities",
            "cfei_number",
            "cluster_names",
            "context",
            "contingency_pd",
            "country_programme",
            "created",
            "days_from_review_to_signed",
            "days_from_submission_to_signed",
            "document_type",
            "donor_codes",
            "donors",
            "end",
            "equity_narrative",
            "equity_rating",
            "final_partnership_review",
            "flagged_sections",
            "flat_locations",
            "frs",
            "frs_details",
            "gender_narrative",
            "gender_rating",
            "grants",
            "humanitarian_flag",
            "hq_support_cost",
            "id",
            "implementation_strategy",
            "in_amendment",
            "ip_program_contribution",
            "location_names",
            "location_p_codes",
            "locations",
            "management_budgets",
            "metadata",
            "modified",
            "number",
            "offices",
            "other_info",
            "other_partners_involved",
            "partner",
            "partner_authorized_officer_signatory",
            "partner_focal_points",
            "partner_id",
            "partner_vendor",
            "permissions",
            "planned_budget",
            "planned_visits",
            "population_focus",
            "prc_review_attachment",
            "prc_review_document",
            "prc_review_document_file",
            "quarters",
            "reference_number_year",
            "result_links",
            "review_date_prc",
            "risks",
            "section_names",
            "sections",
            "signed_by_partner_date",
            "signed_by_unicef_date",
            "signed_pd_attachment",
            "signed_pd_document",
            "signed_pd_document_file",
            "start",
            "status",
            "status_list",
            "submission_date",
            "submission_date_prc",
            "submitted_to_prc",
            "supply_items",
            "sustainability_narrative",
            "sustainability_rating",
            "technical_guidance",
            "termination_doc_attachment",
            "termination_doc_file",
            "title",
            "unicef_focal_points",
            "unicef_signatory",
        )


class InterventionDummySerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervention
        fields = ()


class PMPInterventionAttachmentSerializer(InterventionAttachmentSerializer):
    class Meta(InterventionAttachmentSerializer.Meta):
        extra_kwargs = {
            'intervention': {'read_only': True},
        }
