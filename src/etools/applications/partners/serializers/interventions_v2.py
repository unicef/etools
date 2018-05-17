from datetime import date
from operator import itemgetter

from django.db import transaction
from django.db.models import Q
from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.serializers import ValidationError

from etools.applications.attachments.serializers_fields import AttachmentSingleFileField
from etools.applications.EquiTrack.serializers import SnapshotModelSerializer
from etools.applications.funds.models import FundsCommitmentItem, FundsReservationHeader
from etools.applications.funds.serializers import FRsSerializer
from etools.applications.locations.serializers import LocationLightSerializer, LocationSerializer
from etools.applications.partners.models import (Intervention, InterventionAmendment, InterventionAttachment,
                                                 InterventionBudget, InterventionPlannedVisits,
                                                 InterventionReportingPeriod, InterventionResultLink,
                                                 InterventionSectorLocationLink,)
from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.reports.models import AppliedIndicator, LowerResult, ReportingRequirement
from etools.applications.reports.serializers.v1 import SectorSerializer
from etools.applications.reports.serializers.v2 import (IndicatorSerializer, LowerResultCUSerializer,
                                                        LowerResultSerializer, ReportingRequirementSerializer,)


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


class InterventionAmendmentCUSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)
    signed_amendment_attachment = AttachmentSingleFileField(read_only=True)

    class Meta:
        model = InterventionAmendment
        fields = "__all__"

    def validate(self, data):
        data = super(InterventionAmendmentCUSerializer, self).validate(data)

        if 'signed_date' in data and data['signed_date'] > date.today():
            raise ValidationError("Date cannot be in the future!")

        if 'intervention' in data:
            if data['intervention'].in_amendment is True:
                raise ValidationError("Cannot add a new amendment while another amendment is in progress.")
            if data['intervention'].agreement.partner.blocked is True:
                raise ValidationError("Cannot add a new amendment while the partner is blocked in Vision.")
        return data


class PlannedVisitsCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = "__all__"


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
        return [l.name for l in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [l.pk for l in obj.sections.all()]

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
            'budget_currency'
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
        )


# TODO intervention sector locations cleanup
class InterventionLocationSectorNestedSerializer(serializers.ModelSerializer):
    locations = LocationLightSerializer(many=True)
    sector = SectorSerializer()

    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'sector', 'locations'
        )


# TODO intervention sector locations cleanup
class InterventionSectorLocationCUSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'intervention', 'sector', 'locations'
        )


class InterventionAttachmentSerializer(serializers.ModelSerializer):
    attachment_file = serializers.FileField(source="attachment", read_only=True)
    attachment_document = AttachmentSingleFileField(source="attachment_file", read_only=True)

    class Meta:
        model = InterventionAttachment
        fields = (
            'id',
            'intervention',
            'created',
            'type',
            'attachment',
            'attachment_file',
            'attachment_document',
        )


class InterventionResultNestedSerializer(serializers.ModelSerializer):
    cp_output_name = serializers.CharField(source="cp_output.output_name", read_only=True)
    ram_indicator_names = serializers.SerializerMethodField(read_only=True)
    ll_results = LowerResultSerializer(many=True, read_only=True)

    def get_ram_indicator_names(self, obj):
        return [i.name for i in obj.ram_indicators.all()]

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

        return super(InterventionResultLinkSimpleCUSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        intervention = validated_data.get('intervention')
        if intervention and intervention.agreement.partner.blocked is True:
            raise ValidationError("An Output cannot be updated for a partner that is blocked in Vision")
        return super(InterventionResultLinkSimpleCUSerializer, self).create(validated_data)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"


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
        instance = super(InterventionResultCUSerializer, self).create(validated_data)
        self.update_ll_results(instance, ll_results)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        ll_results = self.context.pop('ll_results', [])
        self.update_ll_results(instance, ll_results)
        return super(InterventionResultCUSerializer, self).update(instance, validated_data)


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


class InterventionCreateUpdateSerializer(SnapshotModelSerializer):

    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    prc_review_attachment = AttachmentSingleFileField(read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
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
        return super(InterventionCreateUpdateSerializer, self).to_internal_value(data)

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
        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)
        return updated


class InterventionDetailSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    prc_review_attachment = AttachmentSingleFileField(read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    submitted_to_prc = serializers.ReadOnlyField()
    frs_details = FRsSerializer(source='frs', read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)
    flagged_sections = serializers.SerializerMethodField(read_only=True)
    section_names = serializers.SerializerMethodField(read_only=True)
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
        return [l.id for l in obj.intervention_locations]

    def get_location_names(self, obj):
        return ['{} [{} - {}]'.format(l.name, l.gateway.name, l.p_code) for l in obj.intervention_locations]

    def get_section_names(self, obj):
        return [l.name for l in obj.flagged_sections]

    def get_flagged_sections(self, obj):
        return [l.id for l in obj.flagged_sections]

    def get_cluster_names(self, obj):
        return [c for c in obj.intervention_clusters]

    class Meta:
        model = Intervention
        fields = (
            "id", 'frs', "partner", "agreement", "document_type", "number", "prc_review_document_file", "frs_details",
            "signed_pd_document_file", "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "submitted_to_prc", "signed_pd_document", "signed_by_unicef_date",
            "unicef_signatory", "unicef_focal_points", "partner_focal_points", "partner_authorized_officer_signatory",
            "offices", "population_focus", "signed_by_partner_date", "created", "modified",
            "planned_budget", "result_links", 'country_programme', 'metadata', 'contingency_pd', "amendments",
            "attachments", 'permissions', 'partner_id', "sections",
            "locations", "location_names", "cluster_names", "flat_locations", "flagged_sections", "section_names",
            "in_amendment", "prc_review_attachment", "signed_pd_attachment", "donors", "donor_codes", "grants",
            "location_p_codes"
        )


class InterventionListMapSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id')
    locations = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    def get_locations(self, obj):
        return [LocationSerializer().to_representation(l) for l in obj.intervention_locations]

    def get_sections(self, obj):
        return [s.id for s in obj.flagged_sections]

    class Meta:
        model = Intervention
        fields = (
            "id", "partner_id", "partner_name", "agreement", "document_type", "number", "title", "status",
            "start", "end", "offices", "sections", "locations"
        )


class InterventionReportingRequirementListSerializer(serializers.ModelSerializer):
    reporting_requirements = ReportingRequirementSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Intervention
        fields = ("reporting_requirements", )


class InterventionReportingRequirementCreateSerializer(serializers.ModelSerializer):
    report_type = serializers.ChoiceField(
        choices=ReportingRequirement.TYPE_CHOICES
    )
    reporting_requirements = ReportingRequirementSerializer(many=True)

    class Meta:
        model = Intervention
        fields = ("reporting_requirements", "report_type", )

    def _validate_qpr(self, requirements):
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

        # Ensure start date is after previous end date
        for i in range(1, len(requirements)):
            if requirements[i]["start_date"] <= requirements[i - 1]["end_date"]:
                raise serializers.ValidationError({
                    "reporting_requirements": {
                        "start_date": _(
                            "Start date needs to be after previous end date."
                        )
                    }
                })

    def _validate_hr(self):
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

    def _merge_data(self, data):
        current_reqs = ReportingRequirement.objects.values(
            "id",
            "start_date",
            "end_date",
            "due_date",
        ).filter(
            intervention=self.intervention,
            report_type=data["report_type"],
        )

        current_reqs_dict = {}
        for r in current_reqs:
            current_reqs_dict[r["due_date"]] = r

        report_type = data["report_type"]
        for r in data["reporting_requirements"]:
            # not expecting ids, so match based on due date
            if r.get("due_date") in current_reqs_dict:
                r["id"] = current_reqs_dict[r.get("due_date")]["id"]
                current_reqs_dict.pop(r["due_date"])

            r["intervention"] = self.intervention
            r["report_type"] = report_type
            if report_type == ReportingRequirement.TYPE_HR:
                r["end_date"] = r["due_date"]
                r["start_date"] = None

        # We need all reporting requirements in end date order
        data["reporting_requirements"] = sorted(
            data["reporting_requirements"],
            key=itemgetter("end_date")
        )
        return data

    def run_validation(self, initial_data):
        serializer = self.fields["reporting_requirements"].child
        report_type = initial_data.get("report_type")
        if report_type == ReportingRequirement.TYPE_QPR:
            serializer.fields["start_date"].required = True
            serializer.fields["end_date"].required = True
        return super().run_validation(initial_data)

    def validate(self, data):
        """The first reporting requirement's start date needs to be
        on or after the PD start date.
        Subsequent reporting requirements start date needs to be after the
        previous reporting requirement end date.
        """
        self.intervention = self.context["intervention"]

        # Only able to change reporting requirements when PD
        # is in amendment status
        if not self.intervention.in_amendment and self.intervention.status != Intervention.DRAFT:
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

        self._merge_data(data)

        if data["report_type"] == ReportingRequirement.TYPE_QPR:
            self._validate_qpr(data["reporting_requirements"])
        elif data["report_type"] == ReportingRequirement.TYPE_HR:
            self._validate_hr()

        return data

    def create(self, validated_data):
        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                pk = r.pop("id")
                ReportingRequirement.objects.filter(pk=pk).update(**r)
            else:
                ReportingRequirement.objects.create(**r)
        return self.intervention

    def delete(self, validated_data):
        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                ReportingRequirement.objects.filter(pk=r.get("id")).delete()
        return self.intervention
