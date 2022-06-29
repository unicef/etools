import codecs
import csv
import decimal
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField

from etools.applications.field_monitoring.fm_settings.serializers import LocationSiteSerializer
from etools.applications.partners.models import (
    FileType,
    Intervention,
    InterventionAmendment,
    InterventionManagementBudget,
    InterventionManagementBudgetItem,
    InterventionReview,
    InterventionRisk,
    InterventionSupplyItem,
)
from etools.applications.partners.permissions import (
    InterventionPermissions,
    PARTNERSHIP_MANAGER_GROUP,
    PRC_SECRETARY,
    SENIOR_MANAGEMENT_GROUP,
)
from etools.applications.partners.serializers.intervention_snapshot import FullInterventionSnapshotSerializerMixin
from etools.applications.partners.serializers.interventions_v2 import (
    FRsSerializer,
    InterventionAmendmentCUSerializer,
    InterventionAttachmentSerializer,
    InterventionBudgetCUSerializer,
    InterventionListSerializer as InterventionV2ListSerializer,
    InterventionResultNestedSerializer,
    InterventionResultsStructureSerializer,
    PlannedVisitsNestedSerializer,
    SingleInterventionAttachmentField,
)
from etools.applications.partners.serializers.partner_organization_v2 import PartnerStaffMemberUserSerializer
from etools.applications.partners.serializers.v3 import InterventionReviewSerializer
from etools.applications.reports.base.quarters import get_quarters_range
from etools.applications.reports.serializers.v2 import InterventionTimeFrameSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class InterventionRiskSerializer(FullInterventionSnapshotSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = InterventionRisk
        fields = ('id', 'risk_type', 'mitigation_measures', 'intervention')
        kwargs = {'intervention': {'write_only': True}}

    def validate_mitigation_measures(self, value):
        if value and len(value) > 2500:
            raise serializers.ValidationError(
                "This field is limited to {} or less characters.".format(
                    2500,
                ),
            )
        return value

    def get_intervention(self):
        return self.validated_data['intervention']


class InterventionSupplyItemSerializer(FullInterventionSnapshotSerializerMixin, serializers.ModelSerializer):
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
            "unicef_product_number",
            "provided_by",
        )

    def create(self, validated_data):
        validated_data["intervention"] = self.initial_data.get("intervention")
        return super().create(validated_data)

    def get_intervention(self):
        return self.context["intervention"]


class InterventionSupplyItemUploadSerializer(serializers.Serializer):
    required_columns = ["Product Number", "Product Title", "Quantity", "Indicative Price"]

    supply_items_file = serializers.FileField()

    def valid_row(self, row, index):
        # cleanup values before work
        for column in self.required_columns:
            if row.get(column):
                row[column] = row[column].strip()

        # dont parse disclaimer line
        if 'disclaimer' in ''.join(map(str, row.values())).lower():
            return False

        # skip if row is empty
        if not any(row.get(c) for c in self.required_columns):
            return False

        for required_column in self.required_columns:
            if not row.get(required_column):
                raise ValidationError(f"Unable to process row {index}, missing value for `{required_column}`")

        return True

    def extract_file_data(self):
        data = []
        reader = csv.DictReader(
            codecs.iterdecode(
                self.validated_data.get("supply_items_file"),
                "utf-8",
                errors='ignore'
            ),
            delimiter=",",
        )
        for i, row in enumerate(reader):
            index = i + 2  # enumeration starts from zero plus one for header
            if self.valid_row(row, index):
                try:
                    quantity = decimal.Decimal(row["Quantity"])
                except decimal.InvalidOperation:
                    raise ValidationError(f"Unable to process row {index}, bad number provided for `Quantity`")

                try:
                    price = decimal.Decimal(row["Indicative Price"])
                except decimal.InvalidOperation:
                    raise ValidationError(f"Unable to process row {index}, bad number provided for `Indicative Price`")

                title = ''.join([x if x in string.printable else '' for x in row["Product Title"]])
                product_no = ''.join([x if x in string.printable else '' for x in row["Product Number"]])

                data.append((
                    title,
                    quantity,
                    price,
                    product_no,
                ))
        return data


class InterventionManagementBudgetItemSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'invalid_budget': _('Invalid budget data. Total cash should be equal to items number * price per item.')
    }

    id = serializers.IntegerField(required=False)

    class Meta:
        model = InterventionManagementBudgetItem
        fields = (
            'id', 'kind', 'name',
            'unit', 'unit_price', 'no_units',
            'unicef_cash', 'cso_cash'
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = None
        if 'id' in attrs:
            instance = self.Meta.model.objects.filter(id=attrs['id']).first()

        unit_price = attrs.get('unit_price', instance.unit_price if instance else None)
        no_units = attrs.get('no_units', instance.no_units if instance else None)
        unicef_cash = attrs.get('unicef_cash', instance.unicef_cash if instance else None)
        cso_cash = attrs.get('cso_cash', instance.cso_cash if instance else None)

        # unit_price * no_units can contain more decimal places than we're able to save
        if abs((unit_price * no_units) - (unicef_cash + cso_cash)) > 0.01:
            self.fail('invalid_budget')

        return attrs


class InterventionManagementBudgetSerializer(FullInterventionSnapshotSerializerMixin, serializers.ModelSerializer):
    items = InterventionManagementBudgetItemSerializer(many=True, required=False)
    act1_total = serializers.SerializerMethodField()
    act2_total = serializers.SerializerMethodField()
    act3_total = serializers.SerializerMethodField()
    partner_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    unicef_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = InterventionManagementBudget
        fields = (
            "items",
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

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        self.set_items(instance, items)
        return instance

    def set_items(self, instance, items):
        if items is None:
            return

        updated_pks = []
        for i, item in enumerate(items):
            item_instance = instance.items.filter(pk=item.get('id')).first()
            if item_instance:
                serializer = InterventionManagementBudgetItemSerializer(
                    data=item, instance=item_instance, partial=self.partial,
                )
            else:
                serializer = InterventionManagementBudgetItemSerializer(data=item)
            if not serializer.is_valid():
                raise ValidationError({'items': {i: serializer.errors}})

            updated_pks.append(serializer.save(budget=instance).pk)

        # cleanup, remove unused options
        instance.items.exclude(pk__in=updated_pks).delete()

        # doing update in serializer instead of post_save to avoid big number of budget re-calculations
        instance.update_cash()

    def get_intervention(self):
        return self.instance.intervention


class InterventionDetailSerializer(FullInterventionSnapshotSerializerMixin, serializers.ModelSerializer):
    activation_letter_attachment = AttachmentSingleFileField(read_only=True)
    activation_letter_file = serializers.FileField(source='activation_letter', read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    available_actions = serializers.SerializerMethodField()
    budget_owner = MinimalUserSerializer()
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
    sites = LocationSiteSerializer(many=True)
    submitted_to_prc = serializers.ReadOnlyField()
    termination_doc_attachment = AttachmentSingleFileField(read_only=True)
    termination_doc_file = serializers.FileField(source='termination_doc', read_only=True)
    final_partnership_review = SingleInterventionAttachmentField(
        type_name=FileType.FINAL_PARTNERSHIP_REVIEW,
        read_field=InterventionAttachmentSerializer()
    )
    risks = InterventionRiskSerializer(many=True, read_only=True)
    reviews = InterventionReviewSerializer(many=True, read_only=True)
    quarters = InterventionTimeFrameSerializer(many=True, read_only=True)
    supply_items = InterventionSupplyItemSerializer(many=True, read_only=True)
    management_budgets = InterventionManagementBudgetSerializer(read_only=True)
    unicef_signatory = MinimalUserSerializer()
    unicef_focal_points = MinimalUserSerializer(many=True)
    partner_focal_points = PartnerStaffMemberUserSerializer(many=True)
    partner_authorized_officer_signatory = PartnerStaffMemberUserSerializer()
    original_intervention = serializers.SerializerMethodField()

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
                loc.admin_level_name,
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

    def _is_partnership_manager(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            groups__name__in=[PARTNERSHIP_MANAGER_GROUP],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_prc_secretary(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            groups__name__in=[PRC_SECRETARY],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_overall_approver(self, obj, user):
        if not obj.review:
            return False

        return obj.review.overall_approver_id == user.pk

    def _is_partner_user(self, obj, user):
        return user.email in [o.email for o in obj.partner_focal_points.all()]

    def _is_unicef_focal_point(self, obj, user):
        return user.email in [o.email for o in obj.unicef_focal_points.all()]

    def get_available_actions(self, obj):
        default_ordering = [
            "send_to_unicef",
            "send_to_partner",
            "accept",
            "accept_on_behalf_of_partner",
            "individual_review",
            "review",
            "sign",
            "reject_review",
            "send_back_review",
            "unlock",
            "cancel",
            "suspend",
            "unsuspend",
            "terminate",
            "download_comments",
            "export_results",
            "export_pdf",
            "export_xls",
            "amendment_merge",
        ]
        available_actions = [
            "download_comments",
            "export_results",
            "export_pdf",
            "export_xls",
        ]
        user = self.context['request'].user

        # focal point or budget owner
        if self._is_unicef_focal_point(obj, user) or obj.budget_owner == user:
            # amendments should be deleted instead of moving to cancelled/terminated
            if not obj.in_amendment:
                if obj.status in [obj.SIGNED, obj.ACTIVE, obj.IMPLEMENTED, obj.SUSPENDED]:
                    available_actions.append("terminate")
                    if obj.status not in [obj.SUSPENDED]:
                        available_actions.append("suspend")
            if obj.status == obj.SUSPENDED:
                available_actions.append("unsuspend")

        status_is_cancellable = obj.status in [obj.DRAFT, obj.REVIEW, obj.SIGNATURE]
        budget_owner_or_focal_point = obj.budget_owner == user or self._is_unicef_focal_point(obj, user)
        if not obj.in_amendment and status_is_cancellable and budget_owner_or_focal_point:
            available_actions.append("cancel")

        # only overall approver can approve or reject review
        if obj.status == obj.REVIEW and self._is_overall_approver(obj, user):
            available_actions.append("sign")
            available_actions.append("reject_review")

        # prc secretary can send back intervention if not approved yet
        if obj.status == obj.REVIEW and self._is_prc_secretary() and obj.review and obj.review.overall_approval is None:
            available_actions.append("send_back_review")

        # PD is in review and user prc review not started
        if obj.status == obj.REVIEW and obj.review and obj.review.prc_reviews.filter(
            user=user, overall_approval__isnull=True
        ).exists():
            available_actions.append("individual_review")

        if obj.in_amendment and obj.status == obj.SIGNED and obj.budget_owner == user:
            available_actions.append("amendment_merge")

        # if NOT in Development status then we're done
        if obj.status != obj.DRAFT:
            return [action for action in default_ordering if action in available_actions]

        if not obj.partner_accepted and user in obj.unicef_users_involved:
            available_actions.append("accept_on_behalf_of_partner")

        # PD is assigned to UNICEF
        if obj.unicef_court:
            # budget owner
            if obj.budget_owner == user:
                if not obj.unicef_accepted:
                    available_actions.append("accept")
                if obj.unicef_accepted and obj.partner_accepted:
                    available_actions.append("review")

            # any unicef focal point user
            if user in obj.unicef_focal_points.all() or obj.budget_owner == user:
                if not obj.partner_accepted:
                    available_actions.append("send_to_partner")
                available_actions.append("cancel")
                if obj.partner_accepted:
                    available_actions.append("unlock")

        # PD is assigned to Partner
        else:
            # any partner focal point user
            if self._is_partner_user(obj, user):
                if not obj.unicef_court:
                    available_actions.append("send_to_unicef")
                if obj.partner_accepted or obj.unicef_accepted:
                    available_actions.append("unlock")
                if not obj.partner_accepted:
                    available_actions.append("accept")

        return [action for action in default_ordering if action in available_actions]

    def get_status_list(self, obj):
        pre_signed_statuses = [
            obj.DRAFT,
            obj.REVIEW,
            obj.SIGNATURE,
            obj.SIGNED
        ]
        post_signed_statuses = [
            obj.DRAFT,
            obj.SIGNED,
            obj.ACTIVE,
            obj.ENDED,
            obj.CLOSED,
        ]
        if obj.status == obj.SUSPENDED:
            status_list = [obj.SUSPENDED]

        elif obj.status == obj.TERMINATED:
            status_list = [
                obj.TERMINATED,
            ]
        elif obj.status == obj.CANCELLED:
            status_list = [
                obj.CANCELLED,
            ]
        elif obj.status not in [obj.SIGNED, obj.ACTIVE, obj.ENDED, obj.CLOSED]:
            status_list = pre_signed_statuses
        else:
            status_list = post_signed_statuses

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

    def get_original_intervention(self, obj):
        if obj.in_amendment:
            try:
                return obj.amendment.intervention_id
            except InterventionAmendment.DoesNotExist:
                return None
        return None

    class Meta:
        model = Intervention
        fields = (
            "activation_letter_attachment",
            "activation_letter_file",
            "activation_protocol",
            # "actual_amount",
            "agreement",
            "amendments",
            "attachments",
            "available_actions",
            # "budget_currency",
            "budget_owner",
            "cancel_justification",
            "capacity_development",
            "cash_transfer_modalities",
            "cfei_number",
            "cluster_names",
            "confidential",
            "context",
            "contingency_pd",
            "country_programmes",
            # "cp_outputs",
            "created",
            # "cso_contribution",
            "date_partnership_review_performed",
            "date_sent_to_partner",
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
            # "frs_earliest_start_date",
            # "frs_latest_end_date",
            # "frs_total_frs_amt",
            # "frs_total_intervention_amt",
            # "frs_total_outstanding_amt",
            "gender_narrative",
            "gender_rating",
            "grants",
            "hq_support_cost",
            "humanitarian_flag",
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
            # "offices_names",
            "other_info",
            "other_partners_involved",
            "partner",
            "partner_accepted",
            "partner_authorized_officer_signatory",
            "partner_focal_points",
            "partner_id",
            # "partner_name",
            "partner_vendor",
            "permissions",
            "planned_budget",
            "planned_visits",
            "population_focus",
            "prc_review_attachment",
            "prc_review_document_file",
            "quarters",
            "reference_number_year",
            "result_links",
            "review_date_prc",
            "reviews",
            "risks",
            "section_names",
            "sections",
            "signed_by_partner_date",
            "signed_by_unicef_date",
            "signed_pd_attachment",
            "signed_pd_document_file",
            "sites",
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
            "total_budget",
            "total_unicef_budget",
            "unicef_accepted",
            # "unicef_cash",
            "unicef_court",
            "unicef_focal_points",
            "unicef_signatory",
            "original_intervention",
        )

    def get_intervention(self):
        return self.instance


class InterventionDetailResultsStructureSerializer(serializers.ModelSerializer):
    result_links = InterventionResultsStructureSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Intervention
        fields = (
            "result_links",
        )


class PMPInterventionAttachmentSerializer(InterventionAttachmentSerializer):
    class Meta(InterventionAttachmentSerializer.Meta):
        extra_kwargs = {
            'intervention': {'read_only': True},
        }


class InterventionListSerializer(InterventionV2ListSerializer):
    class Meta(InterventionV2ListSerializer.Meta):
        fields = InterventionV2ListSerializer.Meta.fields + (
            'country_programmes',
        )
        # remove old legacy field to avoid inconvenience
        fields = tuple(f for f in fields if f != 'country_programme')


class InterventionReviewActionSerializer(serializers.ModelSerializer):
    review_type = serializers.ChoiceField(required=True, choices=InterventionReview.INTERVENTION_REVIEW_TYPES)

    class Meta:
        model = InterventionReview
        fields = ('id', 'review_type')


class AmendedInterventionReviewActionSerializer(serializers.ModelSerializer):
    review_type = serializers.ChoiceField(required=True, choices=InterventionReview.ALL_REVIEW_TYPES)

    class Meta:
        model = InterventionReview
        fields = ('id', 'review_type')


class InterventionReviewSendBackSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionReview
        fields = ('id', 'sent_back_comment')
        extra_kwargs = {
            'sent_back_comment': {'required': True},
        }
