from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from etools.applications.last_mile.models import PointOfInterest
from etools.applications.last_mile.serializers import PointOfInterestSerializer


class PointOfInterestViewSet(ModelViewSet):
    serializer_class = PointOfInterestSerializer
    queryset = PointOfInterest.objects.select_related('parent').prefetch_related('partner_organization')
    permission_classes = [IsAuthenticated]
