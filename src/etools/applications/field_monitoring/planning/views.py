import logging
from datetime import date

from django.db import transaction
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from etools.applications.field_monitoring.permissions import (
    IsEditAction,
    IsFieldMonitor,
    IsListAction,
    IsObjectAction,
    IsPersonResponsible,
    IsReadAction,
    IsTeamMember,
)
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate, YearPlan
from etools.applications.field_monitoring.planning.serializers import (
    ActivityAttachmentSerializer,
    MonitoringActivityLightSerializer,
    MonitoringActivitySerializer,
    QuestionTemplateSerializer,
    YearPlanSerializer,
)
from etools.applications.field_monitoring.views import FMBaseAttachmentsViewSet, FMBaseViewSet


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


class QuestionTemplateViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):

    permission_classes = FMBaseViewSet.permission_classes + [
        (IsReadAction) | (IsEditAction & IsFieldMonitor)
    ]
    queryset = QuestionTemplate.objects.all()
    serializer_class = QuestionTemplateSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_active', 'partner', 'cp_output', 'intervention',)

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
    queryset = MonitoringActivity.objects.all()
    serializer_class = MonitoringActivitySerializer
    serializer_action_classes = {
        'list': MonitoringActivityLightSerializer
    }
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction |
        (IsEditAction & IsListAction & IsFieldMonitor) |
        (IsEditAction & (IsObjectAction & (IsFieldMonitor | IsTeamMember | IsPersonResponsible)))
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset.prefetch_related('tpm_partner', 'person_responsible', 'location', 'location_site')

        return queryset

    # todo
    # SERIALIZER_MAP = {
    #     'planned_budget': InterventionBudgetCUSerializer,
    #     'planned_visits': PlannedVisitsCUSerializer,
    #     'result_links': InterventionResultCUSerializer
    # }

    # todo: do we update all information including nested data simultaneously?
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # todo
        # related_fields = ['planned_budget',
        #                   'planned_visits',
        #                   'result_links']
        related_fields = []
        # todo
        # nested_related_names = ['ll_results']
        nested_related_names = []
        instance, old_instance, serializer = self.my_update(
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


class ActivityAttachmentsViewSet(FMBaseAttachmentsViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    serializer_class = ActivityAttachmentSerializer
    related_model = MonitoringActivity

    def get_view_name(self):
        return _('Attachments')

    def get_parent_filter(self):
        data = super().get_parent_filter()
        data['code'] = 'attachments'
        return data
