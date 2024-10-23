import codecs
import csv
import decimal
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext as _, gettext_lazy

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.fm_settings.serializers import LocationSiteSerializer
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.funds.serializers import FRsSerializer
from etools.applications.governments.models import GDD, GDDAmendment, GDDResultLink, GDDRisk, GDDSupplyItem
from etools.applications.governments.permissions import (
    GDDPermissions,
    PARTNERSHIP_MANAGER_GROUP,
    PRC_SECRETARY,
    SENIOR_MANAGEMENT_GROUP,
)
from etools.applications.governments.serializers.amendments import GDDAmendmentCUSerializer
from etools.applications.governments.serializers.gdd_snapshot import FullGDDSnapshotSerializerMixin
from etools.applications.governments.serializers.helpers import (
    GDDAttachmentSerializer,
    GDDBudgetCUSerializer,
    GDDPlannedVisitsNestedSerializer,
    GDDReviewSerializer,
    GDDTimeFrameSerializer,
)
from etools.applications.governments.serializers.result_structure import (
    GDDResultCUSerializer,
    GDDResultNestedSerializer,
)
# from etools.applications.governments.serializers.gdds_v2 import (
#     FRsSerializer,
#     GDDAmendmentCUSerializer,
#     GDDAttachmentSerializer,
#     GDDBudgetCUSerializer,
#     GDDListSerializer as GDDV2ListSerializer,
#     GDDResultNestedSerializer,
#     GDDResultsStructureSerializer,
#     PlannedVisitsNestedSerializer,
#     SingleGDDAttachmentField,
# )
from etools.applications.partners.serializers.partner_organization_v2 import PartnerStaffMemberUserSerializer
from etools.applications.partners.utils import get_quarters_range
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class MinimalGDDListSerializer(serializers.ModelSerializer):

    class Meta:
        model = GDD
        fields = (
            'id',
            'title',
            'number',
        )


class RiskSerializer(FullGDDSnapshotSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = GDDRisk
        fields = ('id', 'risk_type', 'mitigation_measures', 'gdd')
        kwargs = {'gdd': {'write_only': True}}

    def validate_mitigation_measures(self, value):
        if value and len(value) > 2500:
            raise serializers.ValidationError(
                _("This field is limited to %d or less characters.") % 2500
            )
        return value

    def get_gdd(self):
        return self.validated_data['gdd']


class SupplyItemSerializer(FullGDDSnapshotSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = GDDSupplyItem
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
        validated_data["gdd"] = self.initial_data.get("gdd")
        return super().create(validated_data)

    def get_gdd(self):
        return self.context["gdd"]


class BaseGDDListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name')
    unicef_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True, max_digits=20, decimal_places=2)
    cso_contribution = serializers.DecimalField(source='total_partner_contribution', read_only=True, max_digits=20,
                                                decimal_places=2)
    total_unicef_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)
    total_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)
    budget_currency = serializers.CharField(source='planned_budget.currency', read_only=True)

    section_names = serializers.SerializerMethodField()
    flagged_sections = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()
    offices_names = serializers.SerializerMethodField()
    frs_earliest_start_date = serializers.DateField(source='frs__start_date__min', read_only=True)
    frs_latest_end_date = serializers.DateField(source='frs__end_date__max', read_only=True)
    frs_total_frs_amt = serializers.DecimalField(
        source='frs__total_amt_local__sum',
        read_only=True,
        max_digits=20,
        decimal_places=2
    )
    frs_total_intervention_amt = serializers.DecimalField(
        source='frs__intervention_amt__sum',
        read_only=True,
        max_digits=20,
        decimal_places=2
    )
    frs_total_outstanding_amt = serializers.DecimalField(
        source='frs__outstanding_amt_local__sum',
        read_only=True,
        max_digits=20,
        decimal_places=2
    )
    actual_amount = serializers.DecimalField(
        source='frs__actual_amt_local__sum',
        read_only=True,
        max_digits=20,
        decimal_places=2
    )

    def get_offices_names(self, obj):
        return [o.name for o in obj.offices.all()]

    def get_cp_outputs(self, obj):
        return [rl.cp_output.id for rl in obj.result_links.all() if rl.cp_output]

    def get_section_names(self, obj):
        return [section.name for section in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [section.pk for section in obj.sections.all()]

    class Meta:
        model = GDD
        fields = (
            'actual_amount',
            'budget_currency',
            'contingency_pd',
            'country_programme',
            'cp_outputs',
            'cso_contribution',
            'end',
            'flagged_sections',
            'frs_earliest_start_date',
            'frs_latest_end_date',
            'frs_total_frs_amt',
            'frs_total_intervention_amt',
            'frs_total_outstanding_amt',
            'id',
            'metadata',
            'number',
            'offices',
            'offices_names',
            'partner_name',
            'section_names',
            'sections',
            'start',
            'status',
            'title',
            'total_budget',
            'total_unicef_budget',
            'unicef_cash',
            'unicef_focal_points',
        )


class GDDListSerializer(BaseGDDListSerializer):
    fr_currencies_are_consistent = serializers.SerializerMethodField()
    all_currencies_are_consistent = serializers.SerializerMethodField()
    fr_currency = serializers.SerializerMethodField()
    multi_curr_flag = serializers.BooleanField()

    donors = serializers.SerializerMethodField()
    donor_codes = serializers.SerializerMethodField()
    grants = serializers.SerializerMethodField()

    location_p_codes = serializers.SerializerMethodField()

    def get_location_p_codes(self, obj):
        return obj.location_p_codes.split('|') if obj.location_p_codes else []

    def get_donors(self, obj):
        return obj.donors.split('|') if obj.donors else []

    def get_donor_codes(self, obj):
        return obj.donor_codes.split('|') if obj.donor_codes else []

    def get_grants(self, obj):
        return obj.grants.split('|') if obj.grants else []

    def fr_currencies_ok(self, obj):
        return obj.frs__currency__count == 1 if obj.frs__currency__count else None

    def get_fr_currencies_are_consistent(self, obj):
        return self.fr_currencies_ok(obj)

    def get_all_currencies_are_consistent(self, obj):
        if not hasattr(obj, 'planned_budget'):
            return False
        return self.fr_currencies_ok(obj) and obj.max_fr_currency == obj.planned_budget.currency

    def get_fr_currency(self, obj):
        return obj.max_fr_currency if self.fr_currencies_ok(obj) else ''

    class Meta(BaseGDDListSerializer.Meta):
        fields = BaseGDDListSerializer.Meta.fields + (
            'all_currencies_are_consistent',
            'donor_codes',
            'donors',
            'fr_currencies_are_consistent',
            'fr_currency',
            'grants',
            'location_p_codes',
            'multi_curr_flag',
            'humanitarian_flag',
            'unicef_court',
            'date_sent_to_partner',
            'unicef_accepted',
            'partner_accepted',
            'submission_date',
            'cfei_number',
            'context',
            'implementation_strategy',
            'other_details',
            'gender_rating',
            'gender_narrative',
            'equity_rating',
            'equity_narrative',
            'sustainability_rating',
            'sustainability_narrative',
            'ip_program_contribution',
            'budget_owner',
            'hq_support_cost',
            'cash_transfer_modalities',
            'unicef_review_type',
            'cfei_number',
        )


class GDDDetailSerializer(
    FullGDDSnapshotSerializerMixin,
    serializers.ModelSerializer,
):
    activation_letter_attachment = AttachmentSingleFileField(read_only=True)
    amendments = GDDAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = GDDAttachmentSerializer(many=True, read_only=True, required=False)
    available_actions = serializers.SerializerMethodField()
    budget_owner = MinimalUserSerializer()
    status_list = serializers.SerializerMethodField()
    # cluster_names = serializers.SerializerMethodField()
    days_from_review_to_approved = serializers.CharField(read_only=True)
    days_from_submission_to_approved = serializers.CharField(read_only=True)
    donor_codes = serializers.SerializerMethodField()
    donors = serializers.SerializerMethodField()
    flagged_sections = serializers.SerializerMethodField(read_only=True)
    frs_details = FRsSerializer(source='frs', read_only=True)
    grants = serializers.SerializerMethodField()
    location_names = serializers.SerializerMethodField()
    location_p_codes = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    partner = serializers.CharField(source='partner.name', read_only=True)
    partner_id = serializers.CharField(source='partner.id')
    partner_vendor = serializers.CharField(source='partner.vendor_number', read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)
    planned_budget = GDDBudgetCUSerializer(read_only=True)
    planned_visits = GDDPlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    prc_review_attachment = AttachmentSingleFileField(required=False)
    result_links = GDDResultNestedSerializer(many=True, read_only=True, required=False)
    section_names = serializers.SerializerMethodField(read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
    sites = LocationSiteSerializer(many=True)
    submitted_to_prc = serializers.ReadOnlyField()
    termination_doc_attachment = AttachmentSingleFileField(read_only=True)
    final_partnership_review = AttachmentSingleFileField(read_only=True)
    risks = RiskSerializer(many=True, read_only=True)
    reviews = GDDReviewSerializer(many=True, read_only=True)
    quarters = GDDTimeFrameSerializer(many=True, read_only=True)
    supply_items = SupplyItemSerializer(many=True, read_only=True)
    unicef_signatory = MinimalUserSerializer()
    unicef_focal_points = MinimalUserSerializer(many=True)
    partner_focal_points = PartnerStaffMemberUserSerializer(many=True)
    partner_authorized_officer_signatory = PartnerStaffMemberUserSerializer()
    original_gdd = serializers.SerializerMethodField()
    in_amendment_date = serializers.SerializerMethodField()

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
        if 'permissions' in self.context:
            return self.context['permissions']
        user = self.context['request'].user
        ps = GDD.permission_structure()
        permissions = GDDPermissions(
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

    # def get_cluster_names(self, obj):
    #     return [c for c in obj.gdd_clusters()]

    def get_in_amendment_date(self, obj):
        return obj.amendment.created if hasattr(obj, 'amendment') else None

    def _is_management(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            realms__group__name__in=[SENIOR_MANAGEMENT_GROUP],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_partnership_manager(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            realms__group__name__in=[PARTNERSHIP_MANAGER_GROUP],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_prc_secretary(self):
        return get_user_model().objects.filter(
            pk=self.context['request'].user.pk,
            realms__group__name__in=[PRC_SECRETARY],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_overall_approver(self, obj, user):
        if not obj.review:
            return False

        return obj.review.overall_approver_id == user.pk

    def _is_authorized_officer(self, obj, user):
        if not obj.review:
            return False

        return obj.review.authorized_officer_id == user.pk

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
                if obj.status in [obj.APPROVED, obj.ACTIVE, obj.IMPLEMENTED, obj.SUSPENDED]:
                    available_actions.append("terminate")
                    if obj.status not in [obj.SUSPENDED]:
                        available_actions.append("suspend")
            if obj.status == obj.SUSPENDED:
                available_actions.append("unsuspend")

        status_is_cancellable = obj.status in [obj.DRAFT, obj.REVIEW, obj.PENDING_APPROVAL]
        budget_owner_or_focal_point = obj.budget_owner == user or self._is_unicef_focal_point(obj, user)
        if not obj.in_amendment and status_is_cancellable and self._is_prc_secretary():
            available_actions.append("cancel")

        # only overall approver can approve or reject review
        if obj.status == obj.REVIEW and self._is_overall_approver(obj, user):
            available_actions.append("reject_review")


        if obj.status == obj.REVIEW and self._is_authorized_officer(obj, user):
            available_actions.append("reject_review")
            available_actions.append("sign")

        # prc secretary can send back gdd if not approved yet
        if obj.status == obj.REVIEW and self._is_prc_secretary() and obj.review and obj.review.overall_approval is None:
            available_actions.append("send_back_review")

        # PD is in review and user prc review not started
        if obj.status == obj.REVIEW and obj.review and obj.review.gdd_prc_reviews.filter(
            user=user, overall_approval__isnull=True
        ).exists():
            available_actions.append("individual_review")

        if obj.in_amendment and obj.status == obj.APPROVED and budget_owner_or_focal_point:
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
            if budget_owner_or_focal_point:
                if not obj.partner_accepted:
                    available_actions.append("send_to_partner")
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
        pre_approved_statuses = [
            obj.DRAFT,
            obj.REVIEW,
            obj.PENDING_APPROVAL,
            obj.APPROVED
        ]
        post_approved_statuses = [
            obj.DRAFT,
            obj.APPROVED,
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
        elif obj.status not in [obj.APPROVED, obj.ACTIVE, obj.ENDED, obj.CLOSED]:
            status_list = pre_approved_statuses
            # add this to clean up statuses if signature is not required
            if not obj.signature_required:
                status_list.remove(obj.PENDING_APPROVAL)
        else:
            status_list = post_approved_statuses

        return [s for s in obj.INTERVENTION_STATUS if s[0] in status_list]

    def get_quarters(self, obj: GDD):
        return [
            {
                'name': 'Q{}'.format(i + 1),
                'start': quarter[0].strftime('%Y-%m-%d'),
                'end': quarter[1].strftime('%Y-%m-%d')
            }
            for i, quarter in enumerate(get_quarters_range(obj.start, obj.end))
        ]

    def get_original_gdd(self, obj):
        if obj.in_amendment:
            try:
                return obj.amendment.gdd_id
            except GDDAmendment.DoesNotExist:
                return None
        return None

    class Meta:
        model = GDD
        fields = (
            "activation_letter_attachment",
            "activation_protocol",
            "agreement",
            "amendments",
            "attachments",
            "available_actions",
            "budget_owner",
            "cancel_justification",
            "capacity_development",
            "cash_transfer_modalities",
            # "cluster_names",
            "confidential",
            "context",
            "contingency_pd",
            "country_programme",
            "created",
            "date_partnership_review_performed",
            "date_sent_to_partner",
            "days_from_review_to_approved",
            "days_from_submission_to_approved",
            "donor_codes",
            "donors",
            "end",
            "equity_narrative",
            "equity_rating",
            "e_workplans",
            "final_partnership_review",
            "final_review_approved",
            "flagged_sections",
            "flat_locations",
            "frs",
            "frs_details",
            "gender_narrative",
            "gender_rating",
            "grants",
            "has_data_processing_agreement",
            "has_activities_involving_children",
            "has_special_conditions_for_construction",
            "hq_support_cost",
            "humanitarian_flag",
            "id",
            "implementation_strategy",
            "in_amendment",
            "in_amendment_date",
            "ip_program_contribution",
            "location_names",
            "location_p_codes",
            "locations",
            "metadata",
            "modified",
            "number",
            "offices",
            "other_details",
            "other_info",
            "other_partners_involved",
            "partner",
            "partner_accepted",
            "partner_authorized_officer_signatory",
            "partner_focal_points",
            "partner_id",
            "partner_vendor",
            "permissions",
            "planned_budget",
            "planned_visits",
            "population_focus",
            "prc_review_attachment",
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
            "title",
            "total_budget",
            "total_unicef_budget",
            "unicef_accepted",
            "unicef_court",
            "unicef_focal_points",
            "unicef_signatory",
            "original_gdd",
        )

    def get_gdd(self):
        return self.instance


class GDDCreateUpdateSerializer(
    AttachmentSerializerMixin,
    SnapshotModelSerializer,
):

    planned_budget = GDDBudgetCUSerializer(read_only=True)
    prc_review_attachment = AttachmentSingleFileField(required=False)
    signed_pd_attachment = AttachmentSingleFileField(required=False)
    activation_letter_attachment = AttachmentSingleFileField(required=False)
    termination_doc_attachment = AttachmentSingleFileField()
    planned_visits = GDDPlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    attachments = GDDAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = GDDResultCUSerializer(many=True, read_only=True, required=False)
    frs = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=FundsReservationHeader.objects.prefetch_related('gdd').all(),
        required=False,
    )
    final_partnership_review = AttachmentSingleFileField(required=False)

    class Meta:
        model = GDD
        fields = "__all__"

    def to_internal_value(self, data):
        if 'frs' in data:
            if data['frs'] is None:
                data['frs'] = []
        return super().to_internal_value(data)

    def validate_frs(self, frs):
        for fr in frs:
            if fr.gdd:
                if (self.instance is None) or (not self.instance.id) or (fr.gdd.id != self.instance.id):
                    raise ValidationError([
                        _('One or more of the FRs selected is related to a different PD/SPD, %s') % fr.fr_number])
            else:
                pass
                # unicef/etools-issues:779
                # TODO: add this validation back after all legacy data has been handled.
                # make sure it's not expired
                # if fr.expired:
                #     raise ValidationError({'error': 'One or more selected FRs is expired,'
                #                                     ' {}'.format(fr.fr_number)})
        return frs

    def _validate_character_limitation(self, value, limit=5000):
        if value and len(value) > limit:
            raise serializers.ValidationError(
                _("This field is limited to %d or less characters.") % limit
            )
        return value

    def validate_context(self, value):
        return self._validate_character_limitation(value, limit=7000)

    def validate_implementation_strategy(self, value):
        return self._validate_character_limitation(value)

    def validate_ip_program_contribution(self, value):
        return self._validate_character_limitation(value)

    def validate_capacity_development(self, value):
        return self._validate_character_limitation(value)

    def validate_other_details(self, value):
        return self._validate_character_limitation(value)

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.instance and ('start' in validated_data or 'end' in validated_data):
            new_status = validated_data.get('status', None)
            old_status = self.instance.status
            if new_status is not None and new_status == self.instance.TERMINATED and new_status != old_status:
                # no checks required for terminated status
                return validated_data

            start = validated_data.get('start', self.instance.start)
            end = validated_data.get('end', self.instance.end)
            old_quarters = get_quarters_range(self.instance.start, self.instance.end)
            new_quarters = get_quarters_range(start, end)

            if old_quarters and len(old_quarters) > len(new_quarters):
                if new_quarters:
                    last_quarter = new_quarters[-1].quarter
                else:
                    last_quarter = 0

                if self.instance.quarters.filter(
                    quarter__gt=last_quarter,
                    activities__isnull=False,
                ).exists():
                    names_to_be_removed = ', '.join([
                        'Q{}'.format(q.quarter)
                        for q in old_quarters[len(new_quarters):]
                    ])
                    error_text = _('Please adjust activities to not use the '
                                   'quarters to be removed (%(names)s).') % {'names': names_to_be_removed}

                    bad_keys = set(validated_data.keys()).intersection({'start', 'end'})
                    raise ValidationError({key: [error_text] for key in bad_keys})

        return validated_data

    @transaction.atomic
    def update(self, instance, validated_data):
        final_partnership_review = validated_data.pop('final_partnership_review', None)

        updated = super().update(instance, validated_data)

        if final_partnership_review:
            self.get_fields()['final_partnership_review'].set_attachment(instance, final_partnership_review)

        return updated

    def get_gdd(self):
        return self.instance


class GDDResultLinkSimpleCUSerializer(FullGDDSnapshotSerializerMixin, serializers.ModelSerializer):
    cp_output_name = serializers.CharField(source="cp_output.cp_output.name", read_only=True)
    ram_indicator_names = serializers.SerializerMethodField(read_only=True)

    def get_ram_indicator_names(self, obj):
        return [i.name for i in obj.ram_indicators.all()]

    def update(self, instance, validated_data):
        gdd = validated_data.get('gdd', instance.gdd)
        if gdd and gdd.partner.blocked is True:
            raise ValidationError(_("An Output cannot be updated for a government that is blocked in Vision"))

        return super().update(instance, validated_data)

    def create(self, validated_data):
        gdd = validated_data.get('gdd')
        if gdd and gdd.partner.blocked is True:
            raise ValidationError(_("An Output cannot be updated for a government that is blocked in Vision"))
        return super().create(validated_data)

    class Meta:
        model = GDDResultLink
        fields = "__all__"
        read_only_fields = ['code']
        validators = [
            UniqueTogetherValidator(
                queryset=GDDResultLink.objects.all(),
                fields=["gdd", "cp_output"],
                message=gettext_lazy("Invalid CP Output provided.")
            )
        ]

    def get_gdd(self):
        return self.validated_data.get('gdd', getattr(self.instance, 'gdd', None))


class GDDSupplyItemSerializer(FullGDDSnapshotSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = GDDSupplyItem
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
        validated_data["gdd"] = self.initial_data.get("gdd")
        return super().create(validated_data)

    def get_gdd(self):
        return self.context["gdd"]


class GDDSupplyItemUploadSerializer(serializers.Serializer):
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
                raise ValidationError(f"Unable to process row {index}, missing value for '{required_column}'")

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
