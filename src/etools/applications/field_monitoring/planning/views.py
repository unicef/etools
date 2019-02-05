from datetime import date

from django.db.models import Prefetch
from django.http import Http404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from unicef_locations.models import Location
from unicef_locations.serializers import LocationLightSerializer

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import PartnerOrganizationSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.field_monitoring.metadata import PermissionBasedMetadata
from etools.applications.field_monitoring.permissions import UserIsFieldMonitor
from etools.applications.field_monitoring.planning.export.renderers import TaskCSVRenderer
from etools.applications.field_monitoring.planning.export.serializers import TaskExportSerializer
from etools.applications.field_monitoring.planning.filters import TaskSectionsFilter
from etools.applications.field_monitoring.planning.models import YearPlan, Task
from etools.applications.field_monitoring.planning.serializers import YearPlanSerializer, TaskSerializer, \
    TaskListSerializer
from etools.applications.field_monitoring.fm_settings.filters import CPOutputIsActiveFilter
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.field_monitoring.visits.models import Visit
from etools.applications.permissions_simplified.views import SimplePermittedViewSetMixin
from etools.applications.partners.models import PartnerOrganization


class YearPlanViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
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


class TaskViewSet(SimplePermittedViewSetMixin, FMBaseViewSet, viewsets.ModelViewSet):
    metadata_class = PermissionBasedMetadata
    queryset = Task.objects.prefetch_related(
        'cp_output_config', 'cp_output_config__cp_output', 'cp_output_config__sections',
        'partner', 'intervention', 'location', 'location_site', 'sections',
        Prefetch(
            'visits',
            Visit.objects.filter(status=Visit.STATUS_CHOICES.finalized),
            to_attr='completed_visits'
        )
    )
    serializer_class = TaskSerializer
    filter_backends = (TaskSectionsFilter, DjangoFilterBackend, CPOutputIsActiveFilter, OrderingFilter)
    filter_fields = ({
        field: ['exact', 'in'] for field in [
            'cp_output_config__cp_output__parent',
            'cp_output_config', 'partner', 'intervention', 'location', 'location_site',
        ]
    })
    filter_fields['cp_output_config__is_priority'] = ['exact']
    ordering_fields = (
        'cp_output_config__cp_output__name',
        'partner__name', 'intervention__title',
        'location__name', 'location_site__name',
    )
    serializer_action_classes = {
        'list': TaskListSerializer
    }

    def get_view_name(self):
        return _('Plan By Task')

    def perform_create(self, serializer):
        serializer.save(year_plan=self.get_parent_object())

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=[TaskCSVRenderer])
    def export(self, request, *args, **kwargs):
        instances = self.filter_queryset(self.get_queryset())
        serializer = TaskExportSerializer(instances, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tasks_{}_{}.csv'.format(
                self.get_parent_object().year, timezone.now().date())
        })


class PlannedPartnersViewSet(FMBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = PartnerOrganization.objects.filter(tasks__isnull=False).distinct()
    serializer_class = PartnerOrganizationSerializer


class PlannedLocationsViewSet(FMBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Location.objects.filter(tasks__isnull=False).distinct()
    serializer_class = LocationLightSerializer


class PlannedLocationSitesViewSet(FMBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = LocationSite.objects.filter(tasks__isnull=False).distinct()
    serializer_class = LocationSiteLightSerializer
