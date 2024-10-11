from django.core.exceptions import ImproperlyConfigured
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
    GDDReview,
    GDDRisk,
    GDDTimeFrame,
)
from etools.applications.governments.serializers.gdd_snapshot import FullGDDSnapshotSerializerMixin
from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.serializers.interventions_v2 import (
    LocationSiteSerializer,
    PlannedVisitSitesQuarterSerializer,
)
from etools.applications.users.serializers_v3 import MinimalUserSerializer


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
            "unicef_cash_local",
            "currency",
            "total_local",
            "total_unicef_contribution_local",
            "total_cash_local",
            "total_supply"
        )
        read_only_fields = (
            "total_local",
            "total_cash_local",
            "total_supply"
        )

    def get_gdd(self):
        return self.validated_data['gdd']


class GDDAttachmentSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    attachment_file = serializers.FileField(source="attachment", read_only=True)
    attachment_document = AttachmentSingleFileField(
        source="attachment_file",
        override="attachment",
    )

    def update(self, instance, validated_data):
        intervention = validated_data.get('gdd', instance.intervention)
        if intervention and intervention.status in [GDD.ENDED, GDD.CLOSED, GDD.TERMINATED]:
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
            'attachment',
            'attachment_file',
            'attachment_document',
        )


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
                intervention=self.initial_data.get("intervention"),
                pk=self.initial_data.get("id"),
            )
            if self.instance.intervention.agreement.partner.partner_type == OrganizationType.GOVERNMENT:
                raise ValidationError("Planned Visit to be set only at Partner level")
            if self.instance.intervention.status == GDD.TERMINATED:
                raise ValidationError(_("Planned Visit cannot be set for Terminated interventions"))

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
