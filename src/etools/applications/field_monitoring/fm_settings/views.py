from django.utils.translation import ugettext_lazy as _

from rest_framework import generics, mixins, viewsets
from unicef_attachments.models import Attachment
from unicef_locations.models import Location
from unicef_locations.serializers import LocationLightSerializer

from etools.applications.field_monitoring.fm_settings.models import Method
from etools.applications.field_monitoring.fm_settings.serializers import (
    FieldMonitoringGeneralAttachmentSerializer,
    MethodSerializer,
)
from etools.applications.field_monitoring.permissions import IsEditAction, IsPME, IsReadAction, UserIsFieldMonitor
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.permissions_simplified.permissions import PermissionQ as Q


class MethodsViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [
        Q(IsReadAction) | (Q(IsEditAction) & Q(IsPME))
    ]
    # write_permission_classes = [IsPME]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = Method.objects.all()
    serializer_class = MethodSerializer


class FieldMonitoringGeneralAttachmentsViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    viewsets.ModelViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | (Q(IsEditAction) & Q(UserIsFieldMonitor))
    ]
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = Attachment.objects.filter(code='fm_common')
    serializer_class = FieldMonitoringGeneralAttachmentSerializer

    def get_view_name(self):
        return _('Attachments')

    def perform_create(self, serializer):
        serializer.save(code='fm_common')


class InterventionLocationsView(FMBaseViewSet, generics.ListAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationLightSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(intervention_flat_locations=self.kwargs['intervention_pk'])
