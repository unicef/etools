from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from unicef_locations.models import Location
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.action_points.filters import ReferenceNumberOrderingFilter
from etools.applications.field_monitoring.fm_settings.models import CPOutputConfig, LocationSite
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import MinimalCPOutputConfigListSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.field_monitoring.visits.filters import VisitFilter, VisitTeamMembersFilter
from etools.applications.field_monitoring.visits.models import Visit, VisitMethodType
from etools.applications.field_monitoring.visits.serializers import VisitListSerializer, \
    VisitMethodTypeSerializer, VisitSerializer, VisitsTotalSerializers
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.users.serializers import MinimalUserSerializer


class VisitsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = VisitSerializer
    queryset = Visit.objects.prefetch_related(
        'tasks', 'primary_field_monitor', 'team_members',
    ).annotate(tasks__count=Count('tasks'))
    filter_backends = (VisitTeamMembersFilter, DjangoFilterBackend, ReferenceNumberOrderingFilter, OrderingFilter)
    filter_class = VisitFilter
    ordering_fields = (
        'start_date', 'location__name', 'location_site__name', 'status', 'tasks__count',
    )
    serializer_action_classes = {
        'list': VisitListSerializer
    }

    @action(detail=False, methods=['get'], url_path='totals')
    def totals(self, request, *args, **kwargs):
        return Response(
            VisitsTotalSerializers(
                instance=Visit.objects.filter(
                    tasks__year_plan__year=timezone.now().year,
                ).exclude(
                    status__in=[Visit.STATUS_CHOICES.draft, Visit.STATUS_CHOICES.cancelled],
                ).distinct()
            ).data
        )


class VisitsPartnersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = PartnerOrganization.objects.filter(tasks__visits__isnull=False).distinct()
    serializer_class = MinimalPartnerOrganizationListSerializer


class VisitsCPOutputConfigsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = CPOutputConfig.objects.filter(tasks__visits__isnull=False).select_related('cp_output').distinct()
    serializer_class = MinimalCPOutputConfigListSerializer


class VisitsLocationsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Location.objects.filter(visits__isnull=False).distinct()
    serializer_class = LocationLightSerializer


class VisitsLocationSitesViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = LocationSite.objects.filter(visits__isnull=False).distinct()
    serializer_class = LocationSiteLightSerializer


class VisitsTeamMembersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = get_user_model().objects.filter(fm_visits__isnull=False).distinct()
    serializer_class = MinimalUserSerializer


class VisitMethodTypesViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = VisitMethodTypeSerializer
    queryset = VisitMethodType.objects.all()

    def perform_create(self, serializer):
        serializer.save(visit=self.get_parent_object())
