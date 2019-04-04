from rest_framework import generics, status
from rest_framework.response import Response

from etools.applications.action_points.models import ActionPoint
from etools.applications.t2f.helpers.permission_matrix import get_permission_matrix
from etools.applications.t2f.models import ModeOfTravel, TravelType
from etools.applications.t2f.serializers.static_data import StaticDataSerializer


class StaticDataView(generics.GenericAPIView):
    serializer_class = StaticDataSerializer

    def get(self, request):
        data = {
            'travel_types': [c[0] for c in TravelType.CHOICES],
            'travel_modes': [c[0] for c in ModeOfTravel.CHOICES],
            'action_point_statuses': [c[0] for c in ActionPoint.STATUSES],
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)


class PermissionMatrixView(generics.GenericAPIView):
    def get(self, request):
        permission_matrix = get_permission_matrix()
        return Response(permission_matrix, status.HTTP_200_OK)
