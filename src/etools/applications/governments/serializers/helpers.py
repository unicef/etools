from datetime import date, datetime, timedelta
from operator import itemgetter

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from rest_framework import fields, serializers
from rest_framework.relations import RelatedField
from rest_framework.serializers import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.governments.models import (
    GDD,
    GDDAttachment,
    GDDBudget,
    GDDPlannedVisits,
    GDDPlannedVisitSite,
    GDDPRCOfficerReview,
    GDDReportingRequirement,
    GDDReview,
    GDDRisk,
    GDDSpecialReportingRequirement,
    GDDTimeFrame,
)
from etools.applications.governments.serializers.gdd_snapshot import FullGDDSnapshotSerializerMixin
from etools.applications.partners.serializers.interventions_v2 import (
    LocationSiteSerializer,
    PlannedVisitSitesQuarterSerializer,
)
from etools.applications.reports.validators import SpecialReportingRequirementUniqueValidator
from etools.applications.users.serializers_v3 import MinimalUserSerializer
from etools.libraries.pythonlib.hash import h11


class GDDRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = GDDRisk
        fields = [
            'risk_type',
            'mitigation_measures',
        ]


class GDDTimeFrameSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    start = serializers.DateField(source='start_date')
    end = serializers.DateField(source='end_date')

    class Meta:
        model = GDDTimeFrame
        fields = ('id', 'name', 'start', 'end',)

    def get_name(self, obj: GDDTimeFrame):
        return 'Q{}'.format(obj.quarter)


class GDDReviewSerializer(serializers.ModelSerializer):
    created_date = serializers.DateField(read_only=True)
    submitted_by = MinimalUserSerializer(read_only=True)
    overall_approver = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    authorized_officer = SeparatedReadWriteField(read_field=MinimalUserSerializer())

    class Meta:
        model = GDDReview
        fields = (
            'id',
            'amendment',
            'review_type',
            'created_date',
            'submitted_by',
            'review_date',

            'meeting_date',
            'prc_officers',
            'overall_approver',
            'authorized_officer',

            'relationship_is_represented',
            'partner_comparative_advantage',
            'relationships_are_positive',
            'pd_is_relevant',
            'pd_is_guided',
            'ges_considered',
            'budget_is_aligned',
            'supply_issues_considered',

            'overall_comment',
            'actions_list',
            'is_recommended_for_approval',
            'overall_approval',
            'sent_back_comment',
        )
        read_only_fields = (
            'amendment', 'review_type', 'overall_approval', 'sent_back_comment',
        )

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        overall_approver = validated_data.get(
            'overall_approver',
            self.instance.overall_approver if self.instance else None
        )
        authorized_officer = validated_data.get(
            'authorized_officer',
            self.instance.authorized_officer if self.instance else None
        )
        if overall_approver and authorized_officer and overall_approver == authorized_officer:
            raise ValidationError(_('Authorized officer cannot be the same as overall approver.'))
        return validated_data

    def update(self, instance, validated_data):
        self._update_prc_officers(instance, validated_data)
        return super().update(instance, validated_data)

    def _update_prc_officers(self, instance, validated_data):
        new_prc_officers = validated_data.pop('prc_officers', None)
        if new_prc_officers is None:
            return

        original_prc_officers = instance.prc_officers.all()
        diff = set(original_prc_officers) - set(new_prc_officers)
        instance.prc_officers.add(*new_prc_officers)
        instance.prc_officers.remove(*diff)


class GDDBudgetCUSerializer(
    FullGDDSnapshotSerializerMixin,
    serializers.ModelSerializer,
):
    partner_contribution_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount_local = serializers.DecimalField(max_digits=20, decimal_places=2)

    unicef_cash_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_unicef_contribution_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_cash_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_supply = serializers.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        model = GDDBudget
        fields = (
            "id",
            "gdd",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "partner_supply_local",
            "currency",
            "total_partner_contribution_local",
            "total_local",
            "partner_contribution_percent",
            "total_unicef_contribution_local",
            "total_cash_local",
            "total_supply"
        )
        read_only_fields = (
            "total_local",
            "total_cash_local",
            "partner_supply_local",
            "total_partner_contribution_local",
            "total_supply"
        )

    def get_gdd(self):
        return self.validated_data['gdd']


class GDDAttachmentSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    attachment_document = AttachmentSingleFileField(source="attachment")

    def update(self, instance, validated_data):
        gdd = validated_data.get('gdd', instance.gdd)
        if gdd and gdd.status in [GDD.ENDED, GDD.CLOSED, GDD.TERMINATED]:
            raise ValidationError(_('An attachment cannot be changed in statuses "Ended, Closed or Terminated"'))
        return super().update(instance, validated_data)

    class Meta:
        model = GDDAttachment
        fields = (
            'id',
            'gdd',
            'created',
            'type',
            'active',
            'attachment_document',
        )
        extra_kwargs = {
            'gdd': {'read_only': True},
        }


class GDDPlannedVisitSitesQuarterSerializer(fields.ListField):
    child = RelatedField(queryset=LocationSite.objects.all())
    child_serializer = LocationSiteSerializer

    def __init__(self, *args, **kwargs):
        self.quarter = kwargs.pop('quarter', None)
        if self.quarter is None:
            raise ImproperlyConfigured('`quarter` is required')
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data: list[int]):
        return LocationSite.objects.filter(pk__in=data)

    def to_representation(self, data: list[LocationSite]):
        return self.child_serializer(data, many=True).data

    def save(self, planned_visits: GDDPlannedVisits, sites: list[LocationSite]):
        sites = set(site.id for site in sites)
        planned_sites = set(GDDPlannedVisitSite.objects.filter(
            planned_visits=planned_visits,
            quarter=self.quarter,
        ).values_list('site_id', flat=True))
        sites_to_create = sites - planned_sites
        sites_to_delete = planned_sites - sites
        GDDPlannedVisitSite.objects.bulk_create((
            GDDPlannedVisitSite(planned_visits=planned_visits, quarter=self.quarter, site_id=site_id)
            for site_id in sites_to_create
        ))
        GDDPlannedVisitSite.objects.filter(
            planned_visits=planned_visits, quarter=self.quarter, site_id__in=sites_to_delete,
        ).delete()


class GDDPlannedVisitsNestedSerializer(serializers.ModelSerializer):
    programmatic_q1_sites = PlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q1, required=False)
    programmatic_q2_sites = PlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q2, required=False)
    programmatic_q3_sites = PlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q3, required=False)
    programmatic_q4_sites = PlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q4, required=False)

    class Meta:
        model = GDDPlannedVisits
        fields = (
            "id",
            "year",
            'programmatic_q1',
            'programmatic_q1_sites',
            'programmatic_q2',
            'programmatic_q2_sites',
            'programmatic_q3',
            'programmatic_q3_sites',
            'programmatic_q4',
            'programmatic_q4_sites',
        )


class GDDPlannedVisitsCUSerializer(serializers.ModelSerializer):
    programmatic_q1_sites = GDDPlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q1, required=False)
    programmatic_q2_sites = GDDPlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q2, required=False)
    programmatic_q3_sites = GDDPlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q3, required=False)
    programmatic_q4_sites = GDDPlannedVisitSitesQuarterSerializer(quarter=GDDPlannedVisitSite.Q4, required=False)

    class Meta:
        model = GDDPlannedVisits
        fields = (
            'id',
            'gdd',
            'year',
            'programmatic_q1',
            'programmatic_q1_sites',
            'programmatic_q2',
            'programmatic_q2_sites',
            'programmatic_q3',
            'programmatic_q3_sites',
            'programmatic_q4',
            'programmatic_q4_sites',
        )

    def is_valid(self, raise_exception=True):
        try:
            self.instance = self.Meta.model.objects.get(
                gdd=self.initial_data.get("gdd"),
                pk=self.initial_data.get("id"),
            )
            if self.instance.gdd.status == GDD.TERMINATED:
                raise ValidationError(_("Planned Visit cannot be set for Terminated gdds"))

        except self.Meta.model.DoesNotExist:
            self.instance = None
        return super().is_valid(raise_exception=True)

    def create(self, validated_data):
        sites_q1 = validated_data.pop('programmatic_q1_sites', None)
        sites_q2 = validated_data.pop('programmatic_q2_sites', None)
        sites_q3 = validated_data.pop('programmatic_q3_sites', None)
        sites_q4 = validated_data.pop('programmatic_q4_sites', None)
        instance = super().create(validated_data)
        if sites_q1 is not None:
            self.fields['programmatic_q1_sites'].save(instance, sites_q1)
        if sites_q2 is not None:
            self.fields['programmatic_q2_sites'].save(instance, sites_q2)
        if sites_q3 is not None:
            self.fields['programmatic_q3_sites'].save(instance, sites_q3)
        if sites_q4 is not None:
            self.fields['programmatic_q4_sites'].save(instance, sites_q4)
        return instance

    def update(self, instance, validated_data):
        sites_q1 = validated_data.pop('programmatic_q1_sites', None)
        sites_q2 = validated_data.pop('programmatic_q2_sites', None)
        sites_q3 = validated_data.pop('programmatic_q3_sites', None)
        sites_q4 = validated_data.pop('programmatic_q4_sites', None)
        instance = super().update(instance, validated_data)
        if sites_q1 is not None:
            self.fields['programmatic_q1_sites'].save(instance, sites_q1)
        if sites_q2 is not None:
            self.fields['programmatic_q2_sites'].save(instance, sites_q2)
        if sites_q3 is not None:
            self.fields['programmatic_q3_sites'].save(instance, sites_q3)
        if sites_q4 is not None:
            self.fields['programmatic_q4_sites'].save(instance, sites_q4)
        return instance


class GDDReportingRequirementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=True, allow_null=False)
    end_date = serializers.DateField(required=True, allow_null=False)

    class Meta:
        model = GDDReportingRequirement
        fields = ("id", "start_date", "end_date", "due_date", )


class GDDReportingRequirementListSerializer(serializers.ModelSerializer):
    reporting_requirements = GDDReportingRequirementSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = GDD
        fields = ("reporting_requirements", )


class GDDReportingRequirementCreateSerializer(
    FullGDDSnapshotSerializerMixin,
    serializers.ModelSerializer,
):
    report_type = serializers.ChoiceField(
        choices=GDDReportingRequirement.TYPE_CHOICES
    )
    reporting_requirements = GDDReportingRequirementSerializer(many=True)

    class Meta:
        model = GDD
        fields = ("reporting_requirements", "report_type", )

    def _validate_qpr(self, requirements):
        self._validate_start_date(requirements)
        self._validate_end_date(requirements)
        self._validate_date_intervals(requirements)

    def _validate_hr(self, requirements):

        self._validate_start_date(requirements)
        self._validate_end_date(requirements)
        self._validate_date_intervals(requirements)

    def _validate_start_date(self, requirements):
        # Ensure that the first reporting requirement start date
        # is on or after GDD start date
        if requirements[0]["start_date"] < self.gdd.start:
            raise serializers.ValidationError({
                "reporting_requirements": {
                    "start_date": _(
                        _("Start date needs to be on or after GDD start date.")
                    )
                }
            })

    def _validate_end_date(self, requirements):
        # Ensure that the last reporting requirement start date
        # is on or before GDD end date
        if requirements[-1]["end_date"] > self.gdd.end:
            raise serializers.ValidationError({
                "reporting_requirements": {
                    "end_date": _(
                        _("End date needs to be on or before GDD end date.")
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
                            _("End date needs to be after the start date.")
                        )
                    }
                })

            if i > 0:
                if requirements[i]["start_date"] != requirements[i - 1]["end_date"] + timedelta(days=1):
                    raise serializers.ValidationError({
                        "reporting_requirements": {
                            "start_date": _(
                                _("Next start date needs to be one day after previous end date.")
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

        current_reqs = GDDReportingRequirement.objects.values(
            "id",
            "start_date",
            "end_date",
            "due_date",
        ).filter(
            gdd=self.gdd,
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
                    r["gdd"] = self.gdd
            else:
                current_ids_that_need_to_be_kept.append(r['id'])

            r["report_type"] = report_type

        return validated_data, current_ids_that_need_to_be_kept, current_reqs_dict

    def run_validation(self, initial_data):
        serializer = self.fields["reporting_requirements"].child
        serializer.fields["start_date"].required = True
        serializer.fields["end_date"].required = True
        serializer.fields["due_date"].required = True

        return super().run_validation(initial_data)

    def validate(self, data):
        """The first reporting requirement's start date needs to be
        on or after the GDD start date.
        Subsequent reporting requirements start date needs to be after the
        previous reporting requirement end date.
        """
        self.gdd = self.context["gdd"]

        # TODO: [e4] remove this whenever a better validation is decided on. This is out of place but needed as a hotfix
        # take into consideration the reporting requirements edit rights on the gdd
        # move this into permissions when time allows
        permissions = self.context.get("gdd_permissions")
        can_edit = permissions['edit'].get("reporting_requirements") if permissions else True

        if self.gdd.status != GDD.DRAFT:
            if self.gdd.status == GDD.TERMINATED:
                ended = self.gdd.end < datetime.now().date() if self.gdd.end else True
                if ended:
                    raise serializers.ValidationError(
                        _("Changes not allowed when GDD is terminated.")
                    )
            # TODO: [e4] remove this whenever a better validation is decided on.
            # This is out of place but needed as a hotfix, can edit should be checked at the view level consistently
            elif self.gdd.status == GDD.PENDING_APPROVAL and can_edit:
                pass
            else:
                if not self.gdd.in_amendment and not self.gdd.termination_doc_attachment.exists():
                    raise serializers.ValidationError(
                        _("Changes not allowed when GDD not in amendment state.")
                    )

        if not self.gdd.start:
            raise serializers.ValidationError(
                _("GDD needs to have a start date.")
            )

        # Validate reporting requirements first
        if not len(data["reporting_requirements"]):
            raise serializers.ValidationError({
                "reporting_requirements": _("This field cannot be empty.")
            })

        self._order_data(data)
        # Make sure that all reporting requirements that have ids are actually related to current gdd
        for rr in data["reporting_requirements"]:
            try:
                rr_id = rr['id']
                req = GDDReportingRequirement.objects.get(pk=rr_id)
                assert req.gdd.id == self.gdd.id
            except GDDReportingRequirement.DoesNotExist:
                raise serializers.ValidationError(_("Requirement ID passed in does not exist"))
            except AssertionError:
                raise serializers.ValidationError(_("Requirement ID passed in belongs to a different gdd"))
            except KeyError:
                pass

        if data["report_type"] == GDDReportingRequirement.TYPE_QPR:
            self._validate_qpr(data["reporting_requirements"])
        elif data["report_type"] == GDDReportingRequirement.TYPE_HR:
            self._validate_hr(data["reporting_requirements"])

        return data

    @cached_property
    def _past_records_editable(self):
        if self.gdd.status == GDD.DRAFT or \
                (self.gdd.status == GDD.APPROVED and self.gdd.contingency_pd):
            return True
        return False

    @transaction.atomic()
    def create(self, validated_data):
        today = date.today()
        validated_data, current_ids_that_need_to_be_kept, current_reqs_dict = self._tweak_data(validated_data)
        deletable_records = GDDReportingRequirement.objects.exclude(pk__in=current_ids_that_need_to_be_kept). \
            filter(gdd=self.gdd, report_type=validated_data['report_type'])

        if not self._past_records_editable:
            if deletable_records.filter(start_date__lte=today).exists():
                raise ValidationError(_("You're trying to delete a record that has a start date in the past"))

        deletable_records.delete()

        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                pk = r.pop("id")

                # if this is a record that starts in the past and it's not editable and has changes (hash is different)
                if r['start_date'] <= today and not self._past_records_editable and\
                        not current_reqs_dict.get(h11(self._get_hash_key_string(r))):
                    raise ValidationError(_("A record that starts in the passed cannot"
                                          " be modified on a non-draft GDD"))
                GDDReportingRequirement.objects.filter(pk=pk).update(**r)
            else:
                GDDReportingRequirement.objects.create(**r)

        return self.gdd

    def delete(self, validated_data):
        for r in validated_data["reporting_requirements"]:
            if r.get("id"):
                GDDReportingRequirement.objects.filter(pk=r.get("id")).delete()
        return self.gdd

    def get_gdd(self):
        return self.context['gdd']


class GDDSpecialReportingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = GDDSpecialReportingRequirement
        fields = "__all__"
        validators = [
            SpecialReportingRequirementUniqueValidator(
                queryset=GDDSpecialReportingRequirement.objects.all(),
                is_pd=False
            )
        ]


class GDDPRCOfficerReviewSerializer(FullGDDSnapshotSerializerMixin, serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)

    class Meta:
        model = GDDPRCOfficerReview
        fields = (
            'id',
            'user',

            'relationship_is_represented',
            'partner_comparative_advantage',
            'relationships_are_positive',
            'pd_is_relevant',
            'pd_is_guided',
            'ges_considered',
            'budget_is_aligned',
            'supply_issues_considered',

            'overall_comment',
            'overall_approval',
            'review_date',
        )
        read_only_fields = (
            'review_date',
        )

    def update(self, instance, validated_data):
        if validated_data.get('overall_approval') is not None:
            validated_data['review_date'] = timezone.now().date()
        return super().update(instance, validated_data)

    def get_gdd(self):
        return self.instance.overall_review.gdd
