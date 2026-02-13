import logging
import re
from datetime import date

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count, F, JSONField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce, JSONObject
from django.contrib.postgres.aggregates import JSONBAgg
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from unicef_restlib.views import NestedViewSetMixin
from unicef_snapshot.models import Activity as HistoryActivity

from etools.applications.audit.models import UNICEFUser
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.serializers import FMCommonAttachmentSerializer
from etools.applications.field_monitoring.permissions import (
    activity_field_is_editable_permission,
    IsEditAction,
    IsFieldMonitor,
    IsListAction,
    IsMonitoringVisitApprover,
    IsObjectAction,
    IsReadAction,
    IsTeamMember,
    IsVisitLead,
)
from etools.applications.field_monitoring.planning.actions.duplicate_monitoring_activity import (
    DuplicateMonitoringActivity,
    MonitoringActivityNotFound,
)
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.export.renderers import MonitoringActivityCSVRenderer
from etools.applications.field_monitoring.planning.export.serializers import MonitoringActivityExportSerializer
from etools.applications.field_monitoring.planning.filters import (
    CPOutputsFilterSet,
    HactForPartnerFilter,
    InterventionsFilterSet,
    MonitoringActivitiesFilterSet,
    ReferenceNumberOrderingFilter,
    UserNameFilter,
    UserTPMPartnerFilter,
    UserTypeFilter,
)
from etools.applications.field_monitoring.planning.mixins import EmptyQuerysetForExternal
from etools.applications.field_monitoring.planning.models import (
    DummyEWPActivityModel,
    DummyGPDModel,
    FacilityType,
    MonitoringActivity,
    MonitoringActivityActionPoint,
    MonitoringActivityFacilityType,
    TPMConcern,
    VisitGoal,
    YearPlan,
)
from etools.applications.field_monitoring.planning.serializers import (
    CPOutputListSerializer,
    DuplicateMonitoringActivitySerializer,
    FacilityTypeSerializer,
    FMPartnerOrganizationListSerializer,
    FMUserSerializer,
    InterventionWithLinkedInstancesSerializer,
    MonitoringActivityActionPointSerializer,
    MonitoringActivityLightSerializer,
    MonitoringActivityListSerializer,
    MonitoringActivitySerializer,
    TemplatedQuestionSerializer,
    TPMConcernSerializer,
    VisitGoalSerializer,
    YearPlanSerializer,
)
from etools.applications.field_monitoring.views import FMBaseViewSet, LinkedAttachmentsViewSet
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, ResultType, Section
from etools.applications.tpm.models import ThirdPartyMonitor
from etools.applications.users.models import Realm


def _get_list_queryset_annotated(queryset):
    """Single-query list: annotate M2M data via Subquery+JSONBAgg (uses through tables)."""
    PartnersThrough = MonitoringActivity.partners.through
    TeamThrough = MonitoringActivity.team_members.through
    InterventionsThrough = MonitoringActivity.interventions.through
    CPOutputsThrough = MonitoringActivity.cp_outputs.through
    SectionsThrough = MonitoringActivity.sections.through
    VisitGoalsThrough = MonitoringActivity.visit_goals.through
    EWPThrough = MonitoringActivity.ewp_activities.through
    GPDsThrough = MonitoringActivity.gpds.through

    empty_json = Value('[]', output_field=JSONField())

    partners_subq = PartnersThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(id=F('partnerorganization_id'), name=F('partnerorganization__organization__name')))
    ).values('arr')

    team_subq = TeamThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(
            id=F('user_id'),
            name=Coalesce(F('user__first_name'), F('user__last_name')),
            first_name=F('user__first_name'),
            middle_name=F('user__middle_name'),
            last_name=F('user__last_name'),
            is_active=F('user__is_active'),
        ))
    ).values('arr')

    interventions_subq = InterventionsThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(
            id=F('intervention_id'),
            title=F('intervention__title'),
            number=F('intervention__number'),
            document_type=F('intervention__document_type'),
        ))
    ).values('arr')

    cp_outputs_subq = CPOutputsThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(id=F('result_id'), name=F('result__name')))
    ).values('arr')

    sections_subq = SectionsThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(id=F('section_id'), name=F('section__name')))
    ).values('arr')

    visit_goals_subq = VisitGoalsThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(
        arr=JSONBAgg(JSONObject(id=F('visitgoal_id'), name=F('visitgoal__name'), info=F('visitgoal__info')))
    ).values('arr')

    facility_types_subq = MonitoringActivityFacilityType.objects.filter(
        monitoring_activity_id=OuterRef('pk')
    ).values('monitoring_activity_id').annotate(
        arr=JSONBAgg(JSONObject(id=F('facility_type_id'), durations=F('facility_type_durations')))
    ).values('arr')

    ewp_subq = EWPThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(arr=JSONBAgg(F('dummyewpactivitymodel__wbs'))).values('arr')

    gpds_subq = GPDsThrough.objects.filter(monitoringactivity_id=OuterRef('pk')).values(
        'monitoringactivity_id'
    ).annotate(arr=JSONBAgg(F('dummygpdmodel__gpd_ref'))).values('arr')

    # Subquery for location/location_site - avoids N+1 by embedding JSON in main query.
    # apps.get_model inside function avoids module-level import side effects.
    Location = apps.get_model('locations', 'Location')
    LocationSite = apps.get_model('field_monitoring_settings', 'LocationSite')

    location_subq = Location.objects.filter(
        pk=OuterRef('location_id')
    ).annotate(
        j=JSONObject(
            id=F('pk'),
            name=F('name'),
            p_code=F('p_code'),
            admin_level=F('admin_level'),
            is_active=F('is_active'),
            parent_id=F('parent__id'),
            parent_name=F('parent__name'),
            parent_p_code=F('parent__p_code'),
        )
    ).values('j')[:1]

    location_site_subq = LocationSite.objects.filter(
        pk=OuterRef('location_site_id')
    ).annotate(
        j=JSONObject(
            id=F('pk'),
            name=F('name'),
            p_code=F('p_code'),
            is_active=F('is_active'),
            parent_id=F('parent__id'),
            parent_name=F('parent__name'),
            parent_p_code=F('parent__p_code'),
        )
    ).values('j')[:1]

    return queryset.prefetch_related(None).annotate(
        checklists_count=Count('checklists'),
        partners_list=Coalesce(Subquery(partners_subq), empty_json),
        team_members_list=Coalesce(Subquery(team_subq), empty_json),
        interventions_list=Coalesce(Subquery(interventions_subq), empty_json),
        cp_outputs_list=Coalesce(Subquery(cp_outputs_subq), empty_json),
        sections_list=Coalesce(Subquery(sections_subq), empty_json),
        visit_goals_list=Coalesce(Subquery(visit_goals_subq), empty_json),
        facility_types_list=Coalesce(Subquery(facility_types_subq), empty_json),
        ewp_activities_list=Coalesce(Subquery(ewp_subq), empty_json),
        gpds_list=Coalesce(Subquery(gpds_subq), empty_json),
        location_list=Subquery(location_subq),
        location_site_list=Subquery(location_site_subq),
    ).select_related(
        'tpm_partner', 'tpm_partner__organization',
        'visit_lead',
    )


class YearPlanViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    queryset = YearPlan.objects.all()
    serializer_class = YearPlanSerializer

    def get_view_name(self):
        return _('Annual Field Monitoring Rationale')

    def get_years_allowed(self):
        return map(str, [date.today().year, date.today().year + 1])

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(year__in=self.get_years_allowed())

    def get_object(self):
        """ get or create object for specified year. only current & next are allowed"""

        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if self.kwargs[lookup_url_kwarg] not in self.get_years_allowed():
            raise Http404

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        defaults = YearPlan.get_defaults(self.kwargs[lookup_url_kwarg])
        obj = queryset.get_or_create(**filter_kwargs, defaults=defaults)[0]

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class TemplatedQuestionsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    queryset = Question.objects.filter(is_active=True)
    serializer_class = TemplatedQuestionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(level=self.kwargs.get('level'))
        queryset = queryset.prefetch_templates(self.kwargs.get('level'), self.kwargs.get('target_id'))
        return queryset

    def get_serializer(self, *args, **kwargs):
        kwargs.update({
            'level': self.kwargs.get('level'),
            'target_id': self.kwargs.get('target_id'),
        })
        return super().get_serializer(*args, **kwargs)

    def get_view_name(self):
        return _('Templates')


class VisitGoalsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VisitGoal.objects.all()
    serializer_class = VisitGoalSerializer


class FacilityTypesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FacilityType.objects.all()
    serializer_class = FacilityTypeSerializer


class MonitoringActivitiesViewSet(
    ValidatorViewMixin,
    FMBaseViewSet,
    viewsets.ModelViewSet,
):
    """
    Retrieve and Update Agreement.
    """
    queryset = MonitoringActivity.objects\
        .annotate(checklists_count=Count('checklists'))\
        .select_related('tpm_partner', 'tpm_partner__organization',
                        'visit_lead', 'location', 'location__parent',
                        'location_site', 'location_site__parent')\
        .prefetch_related(
            Prefetch(
                'facility_type_relations',
                queryset=MonitoringActivityFacilityType.objects.select_related('facility_type'),
            ),
            'team_members',
            Prefetch('partners', queryset=PartnerOrganization.objects.select_related('organization')),
            'interventions', 'cp_outputs',
            'sections', 'visit_goals',
            'ewp_activities', 'gpds',
        )\
        .order_by("-id")
    serializer_class = MonitoringActivitySerializer
    serializer_action_classes = {
        'list': MonitoringActivityListSerializer
    }
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction |
        (IsEditAction & IsListAction & IsFieldMonitor) |
        (IsEditAction & (IsObjectAction & (IsFieldMonitor | IsVisitLead | IsTeamMember | IsMonitoringVisitApprover)))
    ]
    filter_backends = (
        DjangoFilterBackend, ReferenceNumberOrderingFilter,
        OrderingFilter, SearchFilter, HactForPartnerFilter,
    )
    filterset_class = MonitoringActivitiesFilterSet
    ordering_fields = (
        'start_date', 'end_date', 'location', 'location_site', 'monitor_type', 'checklists_count', 'status'
    )
    search_fields = ('number',)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset = _get_list_queryset_annotated(queryset)
        elif self.action not in ('export',):
            queryset = queryset.prefetch_related('report_reviewers', 'offices').select_related('reviewed_by')

        if not self.request.user.is_unicef_user():
            # we should hide activities before assignment
            # if reject reason available activity should be visible (draft + reject_reason = rejected)
            queryset = queryset.filter(
                Q(visit_lead=self.request.user) | Q(team_members=self.request.user),
                Q(status__in=MonitoringActivity.TPM_AVAILABLE_STATUSES) | ~Q(reject_reason=''),
                tpm_partner__organization=self.request.user.profile.organization,
            )

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        related_fields = []
        nested_related_names = []
        serializer = self.my_create(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )
        instance = serializer.instance

        validator = ActivityValid(instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)

        return Response(
            self.get_serializer_class()(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = []
        nested_related_names = []
        kwargs.update({'related_non_serialized_fields': ['report_reviewers', 'team_members', 'offices']})
        instance, old_instance, _serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        validator = ActivityValid(instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        return Response(self.get_serializer_class()(instance, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['get'], url_path='visit-letter')
    def tpm_visit_letter(self, request, *args, **kwargs):
        ma = self.get_object()
        return render_to_pdf_response(
            request, "fm/visit_letter_pdf.html", context={
                "ma": ma,
                "partners": list(ma.partners.all()),
                "results": list(ma.cp_outputs.all())
            },
            filename="visit_letter_{}.pdf".format(ma.reference_number)
        )

    @action(detail=True, methods=['get'], url_path='pdf')
    def visit_pdf(self, request, *args, **kwargs):
        ma = self.get_object()

        def _sanitize_html(value):
            if not isinstance(value, str):
                return value
            # remove <img ...> tags
            value = re.sub(r'<\s*img[^>]*?>', '', value, flags=re.IGNORECASE)
            # remove style attributes that contain url(...)
            value = re.sub(r'\sstyle=\"[^\"]*?url\([^)]*\)[^\"]*?\"', '', value, flags=re.IGNORECASE)
            value = re.sub(r"\sstyle='[^']*?url\([^)]*\)[^']*?'", '', value, flags=re.IGNORECASE)
            # remove bare url(...) occurrences inside inline CSS
            value = re.sub(r'url\([^)]*\)', '', value, flags=re.IGNORECASE)
            return value

        def _sanitize_overall_findings(findings):
            for item in findings:
                if 'narrative_finding' in item:
                    item['narrative_finding'] = _sanitize_html(item['narrative_finding'])
            return findings

        def _sanitize_summary_findings(findings):
            for item in findings:
                if 'value' in item:
                    item['value'] = _sanitize_html(item['value'])
            return findings

        def _sanitize_data_collected(data_list):
            for checklist in data_list:
                for overall in checklist.get('overall', []):
                    if 'narrative_finding' in overall:
                        overall['narrative_finding'] = _sanitize_html(overall['narrative_finding'])
                    for finding in overall.get('findings', []):
                        if 'value' in finding:
                            finding['value'] = _sanitize_html(finding['value'])
            return data_list
        context = {
            "workspace": connection.tenant.name,
            "ma": ma,
            "field_offices": ', '.join(ma.offices.all().values_list('name', flat=True)),
            "location": f'{str(ma.location)}{" -- {}".format(ma.location.parent.name) if ma.location.parent else ""}',
            "sections": ', '.join(ma.sections.all().values_list('name', flat=True)),
            "partners": ', '.join([partner.name for partner in ma.partners.all()]),
            "team_members": ', '.join([member.full_name for member in ma.team_members.all()]),
            "cp_outputs": ', '.join([cp_out.name for cp_out in ma.cp_outputs.all()]),
            "interventions": ', '.join([str(intervention) for intervention in ma.interventions.all()]),
            "overall_findings": _sanitize_overall_findings(list(ma.activity_overall_findings().values('entity_name', 'narrative_finding', 'on_track'))),
            "summary_findings": _sanitize_summary_findings(list(ma.get_export_activity_questions_overall_findings())),
            "data_collected": _sanitize_data_collected(list(ma.get_export_checklist_findings())),
            "action_points": ma.get_export_action_points(request),
            "related_attachments": ma.get_export_related_attachments(request),
            "reported_attachments": ma.get_export_reported_attachments(request),
            "checklist_attachments": ma.get_export_checklist_attachments(request),
            "mission_completion_date": ma.get_completion_date(),

        }
        return render_to_pdf_response(
            request, "fm/visit_pdf.html", context=context,
            filename="visit_{}.pdf".format(ma.reference_number)
        )

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=(MonitoringActivityCSVRenderer,))
    def export(self, request, *args, **kwargs):
        activities = self.filter_queryset(self.get_queryset())\
            .prefetch_related(None)\
            .prefetch_related(
                'team_members',
                Prefetch('partners', queryset=PartnerOrganization.objects.select_related('organization')),
                'interventions', 'cp_outputs',
                'sections', 'offices',
        )

        serializer = MonitoringActivityExportSerializer(activities, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=monitoring_activities_{}.csv'.format(timezone.now().date())
        })

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, pk, *args, **kwargs):
        serializer = DuplicateMonitoringActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            duplicated_monitoring_activity = DuplicateMonitoringActivity().execute(int(pk), request.data.get('with_checklist'), request.user)
        except MonitoringActivityNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'detail': 'Monitoring Activity not found'})

        return Response(self.get_serializer_class()(duplicated_monitoring_activity, context=self.get_serializer_context()).data,
                        status=status.HTTP_201_CREATED)


class FMUsersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    Endpoint to be used for filtering users by their type (unicef/tpm) and partner in case of tpm
    """

    filter_backends = (SearchFilter, UserTypeFilter, UserTPMPartnerFilter, UserNameFilter)
    search_fields = ('email',)
    queryset = get_user_model().objects\
        .base_qs() \
        .order_by('first_name', 'middle_name', 'last_name')
    serializer_class = FMUserSerializer

    def get_queryset(self):
        user_groups = [UNICEFUser.name, ThirdPartyMonitor.name]
        qs_context = {
            "country": connection.tenant,
            "group__name__in": user_groups
        }
        if not self.request.user.is_unicef_user():
            qs_context.update({"organization": self.request.user.profile.organization})

        context_realms_qs = Realm.objects.filter(**qs_context).select_related('organization__tpmpartner')

        qs = super().get_queryset()\
            .filter(realms__in=context_realms_qs) \
            .prefetch_related(Prefetch('realms', queryset=context_realms_qs)) \
            .annotate(tpm_partner=F('realms__organization__tpmpartner'),
                      has_active_realm=F('realms__is_active')) \
            .distinct()

        return qs


class CPOutputsViewSet(
    FMBaseViewSet,
    EmptyQuerysetForExternal,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CPOutputsFilterSet
    queryset = Result.objects.filter(result_type__name=ResultType.OUTPUT).select_related('result_type').order_by('name')
    serializer_class = CPOutputListSerializer


class InterventionsViewSet(
    FMBaseViewSet,
    EmptyQuerysetForExternal,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = InterventionsFilterSet
    queryset = Intervention.objects.exclude(
        status__in=[
            Intervention.DRAFT, Intervention.SIGNATURE,
            Intervention.SIGNED, Intervention.REVIEW,
            Intervention.EXPIRED, Intervention.CANCELLED
        ]
    ).select_related('agreement').prefetch_related('result_links').order_by('status', 'title')
    serializer_class = InterventionWithLinkedInstancesSerializer


class PartnersViewSet(
    FMBaseViewSet,
    EmptyQuerysetForExternal,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PartnerOrganization.objects.filter(deleted_flag=False).exclude(name='').order_by('name')
    serializer_class = FMPartnerOrganizationListSerializer


class ActivityAttachmentsViewSet(LinkedAttachmentsViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('attachments'))
    ]
    serializer_class = FMCommonAttachmentSerializer
    related_model = MonitoringActivity
    attachment_code = 'attachments'

    def get_view_name(self):
        return _('Attachments')


class MonitoringActivityActionPointViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = MonitoringActivityActionPoint.objects.prefetch_related(
        'author',
        'author__profile',
        'assigned_by',
        'assigned_by__profile',
        'section',
        'office',
        'partner',
        'cp_output__result_type',
        'intervention',
        'category',
        Prefetch(
            'history',
            HistoryActivity.objects.filter(
                Q(action=HistoryActivity.CREATE) | Q(Q(action=HistoryActivity.UPDATE), ~Q(change={}))
            ).select_related('by_user')
        )
    ).select_related('assigned_to', 'assigned_to__profile',)
    serializer_class = MonitoringActivityActionPointSerializer
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('action_points'))
    ]

    def perform_create(self, serializer):
        serializer.save(monitoring_activity=self.get_parent_object())


class TPMConcernsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = TPMConcern.objects.prefetch_related('author', 'author__profile', 'category')
    serializer_class = TPMConcernSerializer
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('tpm_concerns'))
    ]

    def perform_create(self, serializer):
        serializer.save(monitoring_activity=self.get_parent_object())
