import functools
import operator
from datetime import date, datetime

from django.db import models, transaction
from django.db.models import Case, DateTimeField, DurationField, ExpressionWrapper, F, Max, OuterRef, Q, Subquery, When
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from etools_validator.mixins import ValidatorViewMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_csv import renderers as r
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.partners.exports_v2 import (
    PartnerOrganizationCSVRenderer,
    PartnerOrganizationDashboardCsvRenderer,
)
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import (
    Agreement,
    Assessment,
    Intervention,
    PartnerOrganization,
    PartnerPlannedVisits,
    PlannedEngagement,
)
from etools.applications.partners.permissions import (
    AllowSafeAuthenticated,
    PartnershipManagerPermission,
    PartnershipManagerRepPermission,
    PartnershipSeniorManagerPermission,
)
from etools.applications.partners.serializers.exports.partner_organization import (
    AssessmentExportFlatSerializer,
    AssessmentExportSerializer,
    PartnerOrganizationExportFlatSerializer,
    PartnerOrganizationExportSerializer,
)
from etools.applications.partners.serializers.partner_organization_v2 import (
    AssessmentDetailSerializer,
    CoreValuesAssessmentSerializer,
    MinimalPartnerOrganizationListSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerOrganizationDashboardSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationListSerializer,
    PartnerPlannedVisitsSerializer,
    PlannedEngagementNestedSerializer,
    PlannedEngagementSerializer,
)
from etools.applications.partners.tasks import sync_partner
from etools.applications.partners.views.helpers import set_tenant_or_fail
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.models import StringConcat
from etools.libraries.djangolib.views import ExternalModuleFilterMixin


class PartnerOrganizationListAPIView(ExternalModuleFilterMixin, QueryStringFilterMixin, ExportModelMixin,
                                     ListCreateAPIView):
    """
    Create new Partners.
    Returns a list of Partners.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationListSerializer
    permission_classes = (AllowSafeAuthenticated,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        PartnerOrganizationCSVRenderer,
        CSVFlatRenderer
    )
    filters = (
        ('partner_type', 'organization__organization_type__in'),
        ('cso_type', 'organization__cso_type__in'),
        ('rating', 'rating__in'),
        ('sea_risk_rating', 'sea_risk_rating_name__in'),
        ('psea_assessment_date_before', 'psea_assessment_date__lt'),
        ('psea_assessment_date_after', 'psea_assessment_date__gt'),
        ('lead_section', 'lead_section__in'),
    )
    search_terms = ('organization__name__icontains', 'organization__vendor_number__icontains',
                    'organization__short_name__icontains')
    module2filters = {
        'tpm': ['activity__tpmactivity__tpm_visit__tpm_partner__staff_members__user', ],
        'psea': ['psea_assessment__assessor__auditor_firm_staff__user', 'psea_assessment__assessor__user'],
        "pmp": ["organization__realms__user"],
    }
    pagination_class = AppendablePageNumberPagination

    def get_renderer_context(self):
        context = super().get_renderer_context()
        if self.request.query_params.get('format', None) == 'csv':
            context['encoding'] = 'utf-8-sig'
        return context

    def get_serializer_class(self, format=None):
        """
        Use restricted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return PartnerOrganizationExportSerializer
            if query_params.get("format") == 'csv_flat':
                return PartnerOrganizationExportFlatSerializer
        if "verbosity" in query_params.keys():
            if query_params.get("verbosity") == 'minimal':
                return MinimalPartnerOrganizationListSerializer
        return super().get_serializer_class()

    def get_queryset(self, format=None):
        qs = super().get_queryset(module='pmp')
        query_params = self.request.query_params

        workspace = query_params.get('workspace', None)
        if workspace:
            set_tenant_or_fail(workspace)

        if query_params:
            if "values" in query_params.keys():
                # Used for ghost data - filter in all(), and return straight away.
                try:
                    ids = [int(x) for x in query_params.get("values").split(",")]
                except ValueError:
                    raise ValidationError(_("ID values must be integers"))
                else:
                    return PartnerOrganization.objects.filter(id__in=ids)
            queries = []
            queries.extend(self.filter_params())
            queries.append(self.search_params())

            if "hidden" in query_params.keys():
                hidden = None
                if query_params.get("hidden").lower() == "true":
                    hidden = True
                    # return all partners when exporting and hidden=true
                    if query_params.get("format", None) in ['csv', 'csv_flat']:
                        hidden = None
                if query_params.get("hidden").lower() == "false":
                    hidden = False
                if hidden is not None:
                    queries.append(Q(hidden=hidden))

            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)
        return qs

    def list(self, request, format=None):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=partner.csv"

        return response


class PartnerOrganizationDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update PartnerOrganization.
    """
    queryset = PartnerOrganization.objects.select_related('planned_engagement')
    serializer_class = PartnerOrganizationDetailSerializer
    permission_classes = (IsAdminUser,)

    SERIALIZER_MAP = {
        'assessments': AssessmentDetailSerializer,
        'planned_visits': PartnerPlannedVisitsSerializer,
        # TODO REALMS: clean up
        # 'staff_members': PartnerStaffMemberCreateUpdateSerializer,
        'planned_engagement': PlannedEngagementNestedSerializer,
        'core_values_assessments': CoreValuesAssessmentSerializer
    }

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerOrganizationCreateUpdateSerializer
        else:
            return super().get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = [
            'assessments',
            # 'staff_members',    # TODO REALMS: clean up
            'planned_engagement',
            'planned_visits',
            'core_values_assessments'
        ]

        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            **kwargs)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(PartnerOrganizationDetailSerializer(instance).data)


class PartnerOrganizationDashboardAPIView(ExportModelMixin, QueryStringFilterMixin, ListAPIView):
    """Returns a list of Implementing partners for the dashboard."""

    permission_classes = (IsAuthenticated,)
    serializer_class = PartnerOrganizationDashboardSerializer
    base_filename = 'IP_dashboard'
    renderer_classes = (r.JSONRenderer, PartnerOrganizationDashboardCsvRenderer)

    filters = (
        ('pk', 'pk__in'),
        ('partner_type', 'partner_type__in'),
        ('cso_type', 'cso_type__in'),
        ('rating', 'rating__in'),
    )
    search_terms = ('partner__name__icontains', 'vendor_number__icontains')

    queryset = PartnerOrganization.objects.active()

    def get_queryset(self, format=None):

        core_value_assessment_expiring = PartnerOrganization.objects.filter(pk=OuterRef("pk")).annotate(
            times_to_expire=ExpressionWrapper(datetime.today() - F('core_values_assessment_date'),
                                              output_field=DurationField())).values('times_to_expire')

        qs = self.queryset.prefetch_related(
            'agreements__interventions__sections',
            'agreements__interventions__flat_locations',
        ).annotate(
            sections=StringConcat("agreements__interventions__sections__name", separator="|", distinct=True),
            locations=StringConcat("agreements__interventions__flat_locations__name", separator="|", distinct=True),
            core_value_assessment_expiring=Subquery(core_value_assessment_expiring),
        )

        queries = []
        queries.extend(self.filter_params())
        queries.append(self.search_params())
        if queries:
            expression = functools.reduce(operator.and_, queries)
            qs = qs.filter(expression)
        return qs

    def list(self, request, format=None):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        self.update_serializer_data(serializer)

        response = Response(serializer.data)

        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                filename = self.get_filename()
                response['Content-Disposition'] = f"attachment;filename={filename}.csv"
        return response

    def get_filename(self):
        today = date.today().strftime("%Y-%b-%d")
        return f'{self.base_filename}_as_of_{today}'

    def update_serializer_data(self, serializer):
        self._add_programmatic_visits(serializer)
        self._add_action_points(serializer)
        self._add_pca_required(serializer)
        self._add_active_pd_for_non_signed_pca(serializer)

    def _add_programmatic_visits(self, serializer):
        qs = PartnerOrganization.objects.annotate(
            last_pv_date=Max(Case(When(
                agreements__interventions__travel_activities__travel_type=TravelType.PROGRAMME_MONITORING,
                agreements__interventions__travel_activities__travels__traveler=F(
                    'agreements__interventions__travel_activities__primary_traveler'),
                agreements__interventions__travel_activities__travels__status=Travel.COMPLETED,
                then=F('agreements__interventions__travel_activities__date')), output_field=DateTimeField())
            ),
            days_since_last_pv=ExpressionWrapper(datetime.now() - F('last_pv_date'), output_field=DurationField()))
        pv_dates = {}
        for partner in qs:
            pv_dates[partner.pk] = {
                "last_pv_date": partner.last_pv_date,
                "days_last_pv": partner.days_since_last_pv.days if partner.days_since_last_pv else None,
            }

        for item in serializer.data:  # Add last_pv_date
            pk = item["id"]
            item["last_pv_date"] = pv_dates[pk]["last_pv_date"]
            item["days_last_pv"] = pv_dates[pk]["days_last_pv"]
            item["alert_no_recent_pv"] = pv_dates[pk]["days_last_pv"] > 180 if pv_dates[pk]["days_last_pv"] else True
            item["alert_no_pv"] = pv_dates[pk]["days_last_pv"] is None

    def _add_action_points(self, serializer):
        qs = PartnerOrganization.objects.annotate(
            action_points=models.Sum(models.Case(models.When(
                actionpoint__status=ActionPoint.STATUS_OPEN, then=1),
                default=0, output_field=models.IntegerField(), distinct=True)),
        )
        ap = {partner.pk: partner.action_points for partner in qs}
        for item in serializer.data:
            item['action_points'] = ap[item["id"]]

    def _add_pca_required(self, serializer):
        qs = PartnerOrganization.objects.annotate(
            last_intervention_date=Max(
                Case(When(agreements__interventions__document_type__in=[Intervention.PD, Intervention.SSFA],
                          then=F('agreements__interventions__end'))),
            ),
            pca_required=ExpressionWrapper(Max('agreements__country_programme__to_date') - F('last_intervention_date'),
                                           output_field=DurationField())
        )
        pca_required = {partner.pk: partner.pca_required for partner in qs}
        for item in serializer.data:
            ppp = pca_required[item["id"]]
            item['alert_pca_required'] = True if ppp and ppp.days < 0 else False

    def _add_active_pd_for_non_signed_pca(self, serializer):
        # TODO add tests
        flagged_interventions = Intervention.objects.filter(
            document_type__in=[Intervention.PD, Intervention.SPD],
            status__in=[Intervention.ACTIVE, Intervention.SIGNED]).values_list('pk', flat=True)
        qs = PartnerOrganization.objects.filter(
            agreements__interventions__in=flagged_interventions).exclude(
            agreements__status=Agreement.SIGNED).distinct().values_list('pk', flat=True)
        for item in serializer.data:
            item['alert_active_pd_for_ended_pca'] = True if item['id'] in qs else False


class PlannedEngagementAPIView(ListAPIView):

    """
    Returns a list of Planned Engagements.
    """
    permission_classes = (IsAdminUser,)
    queryset = PlannedEngagement.objects.all()
    serializer_class = PlannedEngagementSerializer


class PartnerOrganizationAssessmentListCreateView(ExportModelMixin, ListCreateAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = Assessment.objects.all()
    serializer_class = AssessmentDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self, format=None):
        """Use restricted field set for listing"""
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return AssessmentExportSerializer
            if query_params.get("format") == 'csv_flat':
                return AssessmentExportFlatSerializer
        return super().get_serializer_class()


class PartnerOrganizationAssessmentUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentDetailSerializer
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.completed_date or instance.report:
            raise ValidationError(_("Cannot delete a completed assessment"))
        return super().delete(request, *args, **kwargs)


class PartnerOrganizationAddView(CreateAPIView):
    """Sync Partner given a vendor number (it creates it if it does not exist)"""
    serializer_class = PartnerOrganizationCreateUpdateSerializer
    permission_classes = (PartnershipManagerPermission,)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        vendor = self.request.query_params.get('vendor', None)
        if vendor is None:
            return Response({"error": _("No vendor number provided for Partner Organization")},
                            status=status.HTTP_400_BAD_REQUEST)

        error = sync_partner(vendor, request.user.profile.country)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        partner = PartnerOrganization.objects.get(vendor_number=vendor)
        po_serializer = PartnerOrganizationDetailSerializer(partner)
        return Response(po_serializer.data, status=status.HTTP_201_CREATED)


class PartnerOrganizationDeleteView(DestroyAPIView):
    # todo: permission_classes are ignored here. see comments in InterventionAmendmentDeleteView.delete
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        # TODO: hotfix to be addressed
        raise PermissionDenied()
        # try:
        #     partner = PartnerOrganization.objects.get(id=int(kwargs['pk']))
        # except PartnerOrganization.DoesNotExist:
        #     return Response(status=status.HTTP_404_NOT_FOUND)
        # if partner.agreements.exclude(status='draft').count() > 0:
        #     raise ValidationError(
        #         _("There was a PCA/SSFA signed with this partner or a transaction was performed "
        #           "against this partner. The Partner record cannot be deleted")
        #     )
        # elif TravelActivity.objects.filter(partner=partner).count() > 0:
        #     raise ValidationError(_("This partner has trips associated to it"))
        # elif (partner.total_ct_cp or 0) > 0:
        #     raise ValidationError(_("This partner has cash transactions associated to it"))
        # else:
        #     partner.delete()
        #     return Response(status=status.HTTP_204_NO_CONTENT)


class PartnerNotProgrammaticVisitCompliant(PartnerOrganizationListAPIView):
    def get_queryset(self, format=None):
        return PartnerOrganization.objects.not_programmatic_visit_compliant()


class PartnerNotSpotCheckCompliant(PartnerOrganizationListAPIView):
    def get_queryset(self, format=None):
        return PartnerOrganization.objects.not_spot_check_compliant()


class PartnerNotAssuranceCompliant(PartnerOrganizationListAPIView):
    def get_queryset(self, format=None):
        return PartnerOrganization.objects.not_assurance_compliant()


class PartnerWithSpecialAuditCompleted(PartnerOrganizationListAPIView):
    def get_queryset(self, format=None):
        from etools.applications.audit.models import Engagement
        return PartnerOrganization.objects.filter(
            engagement__engagement_type=Engagement.TYPE_SPECIAL_AUDIT,
            engagement__status=Engagement.FINAL,
            engagement__date_of_draft_report_to_ip__year=datetime.now().year)


class PartnerWithScheduledAuditCompleted(PartnerOrganizationListAPIView):
    def get_queryset(self, format=None):
        from etools.applications.audit.models import Engagement
        return PartnerOrganization.objects.filter(
            engagement__engagement_type=Engagement.TYPE_AUDIT,
            engagement__status=Engagement.FINAL,
            engagement__date_of_draft_report_to_ip__year=datetime.now().year)


class PartnerPlannedVisitsDeleteView(DestroyAPIView):
    permission_classes = (PartnershipSeniorManagerPermission,)

    def delete(self, request, *args, **kwargs):
        partner_planned_visit = get_object_or_404(
            PartnerPlannedVisits,
            pk=int(kwargs['pk'])
        )
        self.check_object_permissions(request, partner_planned_visit)
        partner_planned_visit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
