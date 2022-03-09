import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.utils.translation import gettext_lazy as _

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
    IsObjectAction,
    IsReadAction,
    IsVisitLead,
)
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.filters import (
    CPOutputsFilterSet,
    HactForPartnerFilter,
    InterventionsFilterSet,
    MonitoringActivitiesFilterSet,
    ReferenceNumberOrderingFilter,
    UserTPMPartnerFilter,
    UserTypeFilter,
)
from etools.applications.field_monitoring.planning.models import (
    MonitoringActivity,
    MonitoringActivityActionPoint,
    YearPlan,
)
from etools.applications.field_monitoring.planning.serializers import (
    CPOutputListSerializer,
    FMUserSerializer,
    InterventionWithLinkedInstancesSerializer,
    MonitoringActivityActionPointSerializer,
    MonitoringActivityLightSerializer,
    MonitoringActivitySerializer,
    TemplatedQuestionSerializer,
    YearPlanSerializer,
)
from etools.applications.field_monitoring.views import FMBaseViewSet, LinkedAttachmentsViewSet
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.models import Result, ResultType


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


class MonitoringActivitiesViewSet(
    ValidatorViewMixin,
    FMBaseViewSet,
    viewsets.ModelViewSet,
):
    """
    Retrieve and Update Agreement.
    """
    queryset = MonitoringActivity.objects.annotate(checklists_count=Count('checklists')).select_related(
        'tpm_partner', 'visit_lead', 'location', 'location_site',
    ).prefetch_related(
        'team_members', 'partners', 'interventions', 'cp_outputs'
    ).order_by("-id")
    serializer_class = MonitoringActivitySerializer
    serializer_action_classes = {
        'list': MonitoringActivityLightSerializer
    }
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction |
        (IsEditAction & IsListAction & IsFieldMonitor) |
        (IsEditAction & (IsObjectAction & (IsFieldMonitor | IsVisitLead)))
    ]
    filter_backends = (
        DjangoFilterBackend, ReferenceNumberOrderingFilter,
        OrderingFilter, SearchFilter, HactForPartnerFilter,
    )
    filter_class = MonitoringActivitiesFilterSet
    ordering_fields = (
        'start_date', 'end_date', 'location', 'location_site', 'monitor_type', 'checklists_count', 'status'
    )
    search_fields = ('number',)

    def get_queryset(self):
        queryset = super().get_queryset()

        # todo: change to the user.is_unicef
        if UNICEFUser.name not in [g.name for g in self.request.user.groups.all()]:
            # we should hide activities before assignment
            # if reject reason available activity should be visible (draft + reject_reason = rejected)
            queryset = queryset.filter(
                Q(visit_lead=self.request.user) | Q(team_members=self.request.user),
                Q(status__in=MonitoringActivity.TPM_AVAILABLE_STATUSES) | ~Q(reject_reason=''),
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


class FMUsersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    Endpoint to be used for filtering users by their type (unicef/tpm) and partner in case of tpm
    """

    filter_backends = (SearchFilter, UserTypeFilter, UserTPMPartnerFilter)
    search_fields = ('email',)
    queryset = get_user_model().objects.select_related('tpmpartners_tpmpartnerstaffmember__tpm_partner')
    queryset = queryset.order_by('first_name', 'middle_name', 'last_name')
    serializer_class = FMUserSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().filter(
            Q(profile__country=user.profile.country) | Q(monitoring_activities__isnull=False)
        ).order_by('first_name').distinct()

        return qs


class CPOutputsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = (DjangoFilterBackend,)
    filter_class = CPOutputsFilterSet
    queryset = Result.objects.filter(result_type__name=ResultType.OUTPUT).select_related('result_type').order_by('name')
    serializer_class = CPOutputListSerializer


class InterventionsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = (DjangoFilterBackend,)
    filter_class = InterventionsFilterSet
    queryset = Intervention.objects.filter(
        status__in=[
            Intervention.SIGNED, Intervention.ACTIVE, Intervention.ENDED,
            Intervention.IMPLEMENTED, Intervention.CLOSED,
        ]
    ).select_related('agreement').prefetch_related('result_links').order_by('title')
    serializer_class = InterventionWithLinkedInstancesSerializer


class PartnersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PartnerOrganization.objects.filter(deleted_flag=False).exclude(name='').order_by('name')
    serializer_class = MinimalPartnerOrganizationListSerializer


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
        'author', 'assigned_by', 'section', 'office',
        'partner', 'cp_output__result_type', 'intervention', 'category',
        Prefetch(
            'history',
            HistoryActivity.objects.filter(
                Q(action=HistoryActivity.CREATE) | Q(Q(action=HistoryActivity.UPDATE), ~Q(change={}))
            ).select_related('by_user')
        )
    ).select_related('assigned_to',)
    serializer_class = MonitoringActivityActionPointSerializer
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('action_points'))
    ]

    def perform_create(self, serializer):
        serializer.save(monitoring_activity=self.get_parent_object())
