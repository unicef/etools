from datetime import date, datetime
from operator import itemgetter

from django.db import transaction
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.serializers import ValidationError
from rest_framework.validators import UniqueTogetherValidator
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_locations.serializers import LocationSerializer
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.funds.models import FundsCommitmentItem, FundsReservationHeader
from etools.applications.funds.serializers import FRHeaderSerializer, FRsSerializer
from etools.applications.partners.models import (
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionBudget,
    InterventionPlannedVisits,
    InterventionReportingPeriod,
    InterventionResultLink,
    PartnerType,
)
from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.reports.models import AppliedIndicator, LowerResult, ReportingRequirement
from etools.applications.reports.serializers.v2 import (
    AppliedIndicatorBasicSerializer,
    IndicatorSerializer,
    LowerResultCUSerializer,
    LowerResultSerializer,
    RAMIndicatorSerializer,
    ReportingRequirementSerializer,
)
from etools.libraries.pythonlib.hash import h11


class InterventionBudgetCUSerializer(serializers.ModelSerializer):
    partner_contribution_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    unicef_cash_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount_local = serializers.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        model = InterventionBudget
        fields = (
            "id",
            "intervention",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            'currency'
        )


class InterventionAmendmentCUSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)
    signed_amendment_attachment = AttachmentSingleFileField(
        override="signed_amendment"
    )
    internal_prc_review = AttachmentSingleFileField(required=False)

    class Meta:
        model = InterventionAmendment
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=InterventionAmendment.objects.all(),
                fields=["intervention", "signed_date"],
                message=_("There is already an amendment with this signed date."),
            )
        ]

    def validate(self, data):
        data = super().validate(data)

        if 'signed_date' in data and data['signed_date'] > date.today():
            raise ValidationError("Date cannot be in the future!")

        if 'intervention' in data:
            if data['intervention'].in_amendment is True:
                raise ValidationError("Cannot add a new amendment while another amendment is in progress.")
            if data['intervention'].agreement.partner.blocked is True:
                raise ValidationError("Cannot add a new amendment while the partner is blocked in Vision.")

        if InterventionAmendment.OTHER in data["types"]:
            if "other_description" not in data or not data["other_description"]:
                raise ValidationError("Other description required, if type 'Other' selected.")

        return data


class PlannedVisitsCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = "__all__"

    def is_valid(self, raise_exception=True):
        try:
            self.instance = self.Meta.model.objects.get(
                intervention=self.initial_data.get("intervention"),
                pk=self.initial_data.get("id"),
            )
            if self.instance.intervention.agreement.partner.partner_type == PartnerType.GOVERNMENT:
                raise ValidationError("Planned Visit to be set only at Partner level")
            if self.instance.intervention.status == Intervention.TERMINATED:
                raise ValidationError("Planned Visit cannot be set for Terminated interventions")

        except self.Meta.model.DoesNotExist:
            self.instance = None
        return super().is_valid(raise_exception=True)


class PlannedVisitsNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = (
            "id",
            "year",
            "programmatic_q1",
            "programmatic_q2",
            "programmatic_q3",
            "programmatic_q4",
        )


class BaseInterventionListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name')
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
        return [rl.cp_output.id for rl in obj.result_links.all()]

    def get_section_names(self, obj):
        return [section.name for section in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [section.pk for section in obj.sections.all()]

    class Meta:
        model = Intervention
        fields = (
            'id',
            'number',
            'document_type',
            'partner_name',
            'status',
            'title',
            'start',
            'end',
            'frs_total_frs_amt',
            'unicef_cash',
            'cso_contribution',
            'country_programme',
            'frs_earliest_start_date',
            'frs_latest_end_date',
            'sections',
            'section_names',
            'cp_outputs',
            'unicef_focal_points',
            'frs_total_intervention_amt',
            'frs_total_outstanding_amt',
            'offices',
            'actual_amount',
            'offices_names',
            'total_unicef_budget',
            'total_budget',
            'metadata',
            'flagged_sections',
            'budget_currency',
            'contingency_pd',
        )


class InterventionListSerializer(BaseInterventionListSerializer):
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

    class Meta(BaseInterventionListSerializer.Meta):
        fields = BaseInterventionListSerializer.Meta.fields + (
            'fr_currencies_are_consistent', 'all_currencies_are_consistent', 'fr_currency', 'multi_curr_flag',
            'location_p_codes',
            'donors',
            'donor_codes',
            'grants',
        )


class MinimalInterventionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Intervention
        fields = (
            'id',
            'title',
            'number',
        )


class InterventionToIndicatorsListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name')
    indicators = serializers.SerializerMethodField()

    def get_indicators(self, obj):
        qs = [ai for rl in obj.result_links.all() for ll in rl.ll_results.all() for ai in ll.applied_indicators.all()]
        return AppliedIndicatorBasicSerializer(qs, many=True).data

    class Meta:
        model = Intervention
        fields = (
            'id',
            'title',
            'number',
            'partner_name',
            'status',
            'indicators',
            'sections'
        )


class InterventionAttachmentSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    attachment_file = serializers.FileField(source="attachment", read_only=True)
    attachment_document = AttachmentSingleFileField(
        source="attachment_file",
        override="attachment",
    )

    def update(self, instance, validated_data):
        intervention = validated_data.get('intervention', instance.intervention)
        if intervention and intervention.status in [Intervention.ENDED, Intervention.CLOSED, Intervention.TERMINATED]:
            raise ValidationError('An attachment cannot be changed in statuses "Ended, Closed or Terminated"')
        return super().update(instance, validated_data)

    class Meta:
        model = InterventionAttachment
        fields = (
            'id',
            'intervention',
            'created',
            'type',
            'active',
            'attachment',
            'attachment_file',
            'attachment_document',
        )


class InterventionResultNestedSerializer(serializers.ModelSerializer):
    cp_output_name = serializers.CharField(source="cp_output.output_name", read_only=True)
    ram_indicator_names = serializers.SerializerMethodField(read_only=True)
    ll_results = LowerResultSerializer(many=True, read_only=True)

    def get_ram_indicator_names(self, obj):
        return [i.light_repr for i in obj.ram_indicators.all()]

    class Meta:
        model = InterventionResultLink
        fields = (
            'id', 'intervention',
            'cp_output', 'cp_output_name',
            'ram_indicators', 'ram_indicator_names',
            'll_results'
        )


class InterventionResultLinkSimpleCUSerializer(serializers.ModelSerializer):
    cp_output_name = serializers.CharField(source="cp_output.name", read_only=True)
    ram_indicator_names = serializers.SerializerMethodField(read_only=True)

    def get_ram_indicator_names(self, obj):
        return [i.name for i in obj.ram_indicators.all()]

    def update(self, instance, validated_data):
        intervention = validated_data.get('intervention', instance.intervention)
        if intervention and intervention.agreement.partner.blocked is True:
            raise ValidationError("An Output cannot be updated for a partner that is blocked in Vision")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        intervention = validated_data.get('intervention')
        if intervention and intervention.agreement.partner.blocked is True:
            raise ValidationError("An Output cannot be updated for a partner that is blocked in Vision")
        return super().create(validated_data)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=InterventionResultLink.objects.all(),
                fields=["intervention", "cp_output"],
                message=_("Invalid CP Output provided.")
            )
        ]


class InterventionResultCUSerializer(serializers.ModelSerializer):

    lower_results = LowerResultSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"

    def update_ll_results(self, instance, ll_results):
        ll_results = ll_results if ll_results else []

        for result in ll_results:
            result['result_link'] = instance.pk
            applied_indicators = {'applied_indicators': result.pop('applied_indicators', [])}
            instance_id = result.get('id', None)
            if instance_id:
                try:
                    ll_result_instance = LowerResult.objects.get(pk=instance_id)
                except LowerResult.DoesNotExist:
                    raise ValidationError('lower_result has an id but cannot be found in the db')

                ll_result_serializer = LowerResultCUSerializer(
                    instance=ll_result_instance,
                    data=result,
                    context=applied_indicators,
                    partial=True
                )

            else:
                ll_result_serializer = LowerResultCUSerializer(data=result, context=applied_indicators)

            if ll_result_serializer.is_valid(raise_exception=True):
                ll_result_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        ll_results = self.context.pop('ll_results', [])
        instance = super().create(validated_data)
        self.update_ll_results(instance, ll_results)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        ll_results = self.context.pop('ll_results', [])
        self.update_ll_results(instance, ll_results)
        return super().update(instance, validated_data)


class InterventionReportingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionReportingPeriod
        fields = ('id', 'intervention', 'start_date', 'end_date', 'due_date')

    def validate_intervention(self, value):
        """
        Changing the intervention is not allowed. Users should delete this
        reporting period and create a new one associated with the desired
        intervention.
        """
        if self.instance and value != self.instance.intervention:
            raise ValidationError(
                'Cannot change the intervention that this reporting period is associated with.')
        return value

    def check_date_order(self, start_date, end_date, due_date):
        """
        Validate that start_date <= end_date <= due_date.
        """
        if start_date > end_date:
            raise ValidationError('end_date must be on or after start_date')
        if end_date > due_date:
            raise ValidationError('due_date must be on or after end_date')

    def check_for_overlapping_periods(self, intervention_pk, start_date, end_date):
        """
        Validate that new instance doesn't overlap existing periods for this intervention.
        """
        periods = InterventionReportingPeriod.objects.filter(intervention=intervention_pk)
        if self.instance:
            # exclude ourself
            periods = periods.exclude(pk=self.instance.pk)
        # How to identify overlapping periods: https://stackoverflow.com/a/325939/347942
        if periods.filter(start_date__lt=end_date).filter(end_date__gt=start_date).exists():
            raise ValidationError('This period overlaps an existing reporting period.')

    def validate(self, data):
        """
        Validate that start_date <= end_date <= due_date.
        Validate that new instance doesn't overlap existing periods.
        """
        # If we're creating, we'll have all these values in ``data``. If we're
        # patching, we might not, so get missing values from the existing DB instance
        start_date = data.get('start_date') or self.instance.start_date
        end_date = data.get('end_date') or self.instance.end_date
        due_date = data.get('due_date') or self.instance.due_date
        intervention_pk = data.get('intervention') or self.instance.intervention.pk

        self.check_date_order(start_date, end_date, due_date)
        self.check_for_overlapping_periods(intervention_pk, start_date, end_date)
        return data


class InterventionResultSerializer(serializers.ModelSerializer):
    humanitarian_tag = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    ram = serializers.SerializerMethodField()
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"

    def get_humanitarian_tag(self, obj):
        return "Yes" if obj.cp_output.humanitarian_tag else "No"

    def get_hidden(self, obj):
        return "Yes" if obj.cp_output.hidden else "No"

    def get_ram(self, obj):
        return "Yes" if obj.cp_output.ram else "No"


class InterventionIndicatorSerializer(serializers.ModelSerializer):
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = (
            "intervention",
            "ram_indicators",
        )


class FundingCommitmentNestedSerializer(serializers.ModelSerializer):
    fc_type = serializers.CharField(source='fund_commitment.fc_type')

    class Meta:
        model = FundsCommitmentItem
        fields = (
            "grant_number",
            "wbs",
            "fc_type",
            "fc_ref_number",
            "commitment_amount",
            "commitment_amount_dc",
        )


class InterventionCreateUpdateSerializer(AttachmentSerializerMixin, SnapshotModelSerializer):

    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    prc_review_attachment = AttachmentSingleFileField(required=False)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(required=False)
    activation_letter_file = serializers.FileField(source='activation_letter', read_only=True)
    activation_letter_attachment = AttachmentSingleFileField(required=False)
    termination_doc_file = serializers.FileField(source='termination_doc', read_only=True)
    termination_doc_attachment = AttachmentSingleFileField()
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultCUSerializer(many=True, read_only=True, required=False)
    frs = serializers.PrimaryKeyRelatedField(many=True,
                                             queryset=FundsReservationHeader.objects.prefetch_related('intervention')
                                             .all(),
                                             required=False)

    class Meta:
        model = Intervention
        fields = "__all__"

    def to_internal_value(self, data):
        if 'frs' in data:
            if data['frs'] is None:
                data['frs'] = []
        return super().to_internal_value(data)

    def validate_frs(self, frs):
        for fr in frs:
            if fr.intervention:
                if (self.instance is None) or (not self.instance.id) or (fr.intervention.id != self.instance.id):
                    raise ValidationError(['One or more of the FRs selected is related to a different PD/SSFA,'
                                           ' {}'.format(fr.fr_number)])
            else:
                pass
                # unicef/etools-issues:779
                # TODO: add this validation back after all legacy data has been handled.
                # make sure it's not expired
                # if fr.expired:
                #     raise ValidationError({'error': 'One or more selected FRs is expired,'
                #                                     ' {}'.format(fr.fr_number)})
        return frs

    @transaction.atomic
    def update(self, instance, validated_data):
        updated = super().update(instance, validated_data)
        return updated


class InterventionStandardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Intervention
        fields = ('pk', 'number', 'title', 'status')


class InterventionMonitorSerializer(InterventionStandardSerializer):

    pd_output_names = serializers.SerializerMethodField()

    @staticmethod
    def get_pd_output_names(obj):
        return [ll.name for rl in obj.result_links.all() for ll in rl.ll_results.all()]

    class Meta:
        model = Intervention
        fields = ('pk', 'number', 'title', 'status', 'pd_output_names', 'days_from_last_pv')


class InterventionDetailSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')
    partner_vendor = serializers.CharField(source='agreement.partner.vendor_number')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    prc_review_attachment = AttachmentSingleFileField(read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
    activation_letter_file = serializers.FileField(source='activation_letter', read_only=True)
    activation_letter_attachment = AttachmentSingleFileField(read_only=True)
    termination_doc_file = serializers.FileField(source='termination_doc', read_only=True)
    termination_doc_attachment = AttachmentSingleFileField(read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    submitted_to_prc = serializers.ReadOnlyField()
    frs_details = FRsSerializer(source='frs', read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)
    flagged_sections = serializers.SerializerMethodField(read_only=True)
    section_names = serializers.SerializerMethodField(read_only=True)
    days_from_submission_to_signed = serializers.CharField(read_only=True)
    days_from_review_to_signed = serializers.CharField(read_only=True)
    locations = serializers.SerializerMethodField()
    location_names = serializers.SerializerMethodField()
    cluster_names = serializers.SerializerMethodField()

    donors = serializers.SerializerMethodField()
    donor_codes = serializers.SerializerMethodField()
    grants = serializers.SerializerMethodField()

    location_p_codes = serializers.SerializerMethodField()

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
        permissions = InterventionPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()

    def get_locations(self, obj):
        return [loc.id for loc in obj.flat_locations.all()]

    def get_location_names(self, obj):
        return ['{} [{} - {}]'.format(
            loc.name,
            loc.admin_level_name,
            loc.p_code
        ) for loc in obj.flat_locations.all()]

    def get_section_names(self, obj):
        return [loc.name for loc in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [loc.id for loc in obj.sections.all()]

    def get_cluster_names(self, obj):
        return [c for c in obj.intervention_clusters()]

    class Meta:
        model = Intervention
        fields = (
            "id", 'frs', "partner", "agreement", "document_type", "number", "prc_review_document_file", "frs_details",
            "signed_pd_document_file", "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "submitted_to_prc", "signed_pd_document", "signed_by_unicef_date",
            "unicef_signatory", "unicef_focal_points", "partner_focal_points", "partner_authorized_officer_signatory",
            "offices", "population_focus", "signed_by_partner_date", "created", "modified",
            "planned_budget", "result_links", 'country_programme', 'metadata', 'contingency_pd', "amendments",
            "attachments", 'permissions', 'partner_id', "sections", "planned_visits",
            "locations", "location_names", "cluster_names", "flat_locations", "flagged_sections", "section_names",
            "in_amendment", "prc_review_attachment", "signed_pd_attachment", "donors", "donor_codes", "grants",
            "cfei_number",
            "location_p_codes",
            "days_from_submission_to_signed",
            "days_from_review_to_signed",
            "partner_vendor",
            "reference_number_year",
            "activation_letter_file", "activation_letter_attachment",
            "termination_doc_file", "termination_doc_attachment"
        )


class InterventionListMapSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id')
    locations = LocationSerializer(source="flat_locations", many=True)
    offices = serializers.StringRelatedField(many=True)
    sections = serializers.StringRelatedField(many=True)
    unicef_focal_points = serializers.StringRelatedField(many=True)
    donors = serializers.ReadOnlyField(read_only=True)
    donor_codes = serializers.ReadOnlyField(read_only=True)
    grants = serializers.ReadOnlyField(read_only=True)
    results = serializers.ReadOnlyField(source='cp_output_names', read_only=True)
    clusters = serializers.ReadOnlyField(read_only=True)
    frs = FRHeaderSerializer(many=True, read_only=True)

    class Meta:
        model = Intervention
        fields = (
            "id",
            "partner_id",
            "partner_name",
            "agreement",
            "document_type",
            "number",
            "title",
            "status",
            "start",
            "end",
            "offices",
            "sections",
            "locations",
            "unicef_focal_points",
            "donors",
            "donor_codes",
            "grants",
            "results",
            "clusters",
            "frs",
        )


class InterventionReportingRequirementListSerializer(serializers.ModelSerializer):
    reporting_requirements = ReportingRequirementSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Intervention
        fields = ("reporting_requirements", )


class InterventionRAMIndicatorsListSerializer(serializers.ModelSerializer):

    ram_indicators = RAMIndicatorSerializer(
        many=True,
        read_only=True
    )
    cp_output_name = serializers.CharField(source="cp_output.output_name")

    class Meta:
        model = InterventionResultLink
        fields = ("ram_indicators", "cp_output_name")


class InterventionReportingRequirementCreateSerializer(serializers.ModelSerializer):
    report_type = serializers.ChoiceField(
        choices=ReportingRequirement.TYPE_CHOICES
    )
    reporting_requirements = ReportingRequirementSerializer(many=True)

    class Meta:
        model = Intervention
        fields = ("reporting_requirements", "report_type", )

    def _validate_qpr(self, requirements):
        self._validate_start_date(requirements)
        self._validate_date_intervals(requirements)

    def _validate_hr(self, requirements):
        # Ensure intervention has high frequency or cluster indicators
        indicator_qs = AppliedIndicator.objects.filter(
            lower_result__result_link__intervention=self.intervention
        ).filter(
            Q(is_high_frequency=True) |
            Q(cluster_indicator_id__isnull=False)
        )
        if not indicator_qs.count():
            raise serializers.ValidationError(
                _("Indicator needs to be either cluster or high frequency.")
            )

        self._validate_start_date(requirements)
        self._validate_date_intervals(requirements)

    def _validate_start_date(self, requirements):
        # Ensure that the first reporting requirement start date
        # is on or after PD start date
        if requirements[0]["start_date"] < self.intervention.start:
            raise serializers.ValidationError({
                "reporting_requirements": {
                    "start_date": _(
                        "Start date needs to be on or after PD start date."
                    )
                }
            })

    def _validate_date_intervals(self, requirements):
        # Ensure start date is after previous end date
        for i in range(0, len(requirements)):
            if requirements[i]["start_date"] > requirements[i]["end_date"]:
                raise serializers.ValidationError({
                    "reporting_requirements": {
                        "start_date": _(
                            "End date needs to be after the start date."
                        )
                    }
                })

            if i > 0:
                if (requirements[i]["start_date"] - requirements[i - 1]["end_date"]).days > 1 or \
                        (requirements[i]["start_date"] < requirements[i - 1]["end_date"]):
                    raise serializers.ValidationError({
                        "reporting_requirements": {
                            "start_date": _(
                                "Next start date needs to be one day after previous end date."
                            )
                        }
                    })

    def _order_data(self, data):
        data["reporting_requirements"] = sorted(
            data["reporting_requirements"],
            key=itemgetter("start_date")
        )
        return data

    def _get_hash_key_string(self, record):
        k = str(record["start_date"]) + str(record["end_date"]) + str(record["due_date"])
        return k.encode('utf-8')

    def _tweak_data(self, validated_data):

        current_reqs = ReportingRequirement.objects.values(
            "id",
            "start_date",
            "end_date",
            "due_date",
        ).filter(
            intervention=self.intervention,
            report_type=validated_data["report_type"],
        )

        current_reqs_dict = {}
        for c_r in current_reqs:
            current_reqs_dict[h11(self._get_hash_key_string(c_r))] = c_r

        current_ids_that_need_to_be_kept = []

        # if records don't have id but match a record with an id, assigned the id accordingly
        report_type = validated_data["report_type"]
        for r in validated_data["reporting_requirements"]:
            if not r.get('id'):
                # try to map see if the record already exists in the existing records
                hash_key = h11(self._get_hash_key_string(r))
                if current_reqs_dict.get(hash_key):
                    r['id'] = current_reqs_dict[hash_key]['id']
                    # remove record so we can track which ones are left to be deleted later on.
                    current_ids_that_need_to_be_kept.append(r['id'])
                else:
                    r["intervention"] = self.intervention
            else:
                current_ids_that_need_to_be_kept.append(r['id'])

            r["report_type"] = report_type

        return validated_data, current_ids_that_need_to_be_kept, current_reqs_dict

    def run_validation(self, initial_data):
        serializer = self.fields["reporting_requirements"].child
        serializer.fields["start_date"].required = True
        serializer.fields["end_date"].required = True
        serializer.fields["due_date"].required = True

        serializer.fields["start_date"].allow_null = False
        serializer.fields["end_date"].allow_null = False
        return super().run_validation(initial_data)

    def validate(self, data):
        """The first reporting requirement's start date needs to be
        on or after the PD start date.
        Subsequent reporting requirements start date needs to be after the
        previous reporting requirement end date.
        """
        self.intervention = self.context["intervention"]

        if self.intervention.status != Intervention.DRAFT:
            if self.intervention.status == Intervention.TERMINATED:
                ended = self.intervention.end < datetime.now().date() if self.intervention.end else True
                if ended:
                    raise serializers.ValidationError(
                        _("Changes not allowed when PD is terminated.")
                    )
            elif self.intervention.contingency_pd and self.intervention.status == Intervention.SIGNED:
                pass
            else:
                if not self.intervention.in_amendment and not self.intervention.termination_doc_attachment.exists():
                    raise serializers.ValidationError(
                        _("Changes not allowed when PD not in amendment state.")
                    )

        if not self.intervention.start:
            raise serializers.ValidationError(
                _("PD needs to have a start date.")
            )

        # Validate reporting requirements first
        if not len(data["reporting_requirements"]):
            raise serializers.ValidationError({
                "reporting_requirements": _("This field cannot be empty.")
            })

        self._order_data(data)
        # Make sure that all reporting requirements that have ids are actually related to current intervention
        for rr in data["reporting_requirements"]:
            try:
                rr_id = rr['id']
                req = ReportingRequirement.objects.get(pk=rr_id)
                assert req.intervention.id == self.intervention.id
            except ReportingRequirement.DoesNotExist:
                raise serializers.ValidationError("Requirement ID passed in does not exist")
            except AssertionError:
                raise serializers.ValidationError("Requirement ID passed in belongs to a different intervention")
            except KeyError:
                pass

        if data["report_type"] == ReportingRequirement.TYPE_QPR:
            self._validate_qpr(data["reporting_requirements"])
        elif data["report_type"] == ReportingRequirement.TYPE_HR:
            self._validate_hr(data["reporting_requirements"])

        return data

    @cached_property
    def _past_records_editable(self):
        if self.intervention.status == Intervention.DRAFT or \
                (self.intervention.status == Intervention.SIGNED and self.intervention.contingency_pd):
            return True
        return False

    @transaction.atomic()
    def create(self, validated_data):
        today = date.today()
        validated_data, current_ids_that_need_to_be_kept, current_reqs_dict = self._tweak_data(validated_data)
        deletable_records = ReportingRequirement.objects.exclude(pk__in=current_ids_that_need_to_be_kept). \
            filter(intervention=self.intervention, report_type=validated_data['report_type'])

        if not self._past_records_editable:
            if deletable_records.filter(start_date__lte=today).exists():
                raise ValidationError("You're trying to delete a record that has a start date in the past")

        deletable_records.delete()

        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                pk = r.pop("id")

                # if this is a record that starts in the past and it's not editable and has changes (hash is different)
                if r['start_date'] <= today and not self._past_records_editable and\
                        not current_reqs_dict.get(h11(self._get_hash_key_string(r))):
                    raise ValidationError("A record that starts in the passed cannot"
                                          " be modified on a non-draft PD/SSFA")
                ReportingRequirement.objects.filter(pk=pk).update(**r)
            else:
                ReportingRequirement.objects.create(**r)

        return self.intervention

    def delete(self, validated_data):
        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                ReportingRequirement.objects.filter(pk=r.get("id")).delete()
        return self.intervention


class InterventionLocationExportSerializer(serializers.Serializer):
    partner = serializers.CharField(source="intervention.agreement.partner.name")
    partner_vendor_number = serializers.CharField(source="intervention.agreement.partner.vendor_number")
    pd_ref_number = serializers.CharField(source="intervention.number")
    partnership = serializers.CharField(source="intervention.agreement.agreement_number")
    status = serializers.CharField(source="intervention.status")
    location = serializers.CharField(source="selected_location.name", read_only=True)
    section = serializers.CharField(source="section.name", read_only=True)
    cp_output = serializers.CharField(source="intervention.cp_output_names")
    start = serializers.CharField(source="intervention.start")
    end = serializers.CharField(source="intervention.end")
    focal_point = serializers.CharField(source="intervention.focal_point_names")
    hyperlink = serializers.SerializerMethodField()

    def get_hyperlink(self, obj):
        return 'https://{}/pmp/interventions/{}/details/'.format(self.context['request'].get_host(), obj.intervention.id)
