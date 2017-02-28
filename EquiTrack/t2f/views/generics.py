from __future__ import unicode_literals

from django.conf import settings

from rest_framework import generics, status
from rest_framework.response import Response

from locations.models import Location
from partners.models import PartnerOrganization, Intervention
from reports.models import Result

from t2f.models import TravelType, ModeOfTravel, ActionPoint
from t2f.serializers.static_data import StaticDataSerializer
from t2f.permission_matrix import PERMISSION_MATRIX
from t2f.views import get_filtered_users


class StaticDataView(generics.GenericAPIView):
    serializer_class = StaticDataSerializer

    def get(self, request):
        data = {'partners': PartnerOrganization.objects.all(),
                'partnerships': Intervention.objects.all(),
                'results': Result.objects.all(),
                'locations': Location.objects.all(),
                'travel_types': [c[0] for c in TravelType.CHOICES],
                'travel_modes': [c[0] for c in ModeOfTravel.CHOICES],
                'action_point_statuses': [c[0] for c in ActionPoint.STATUS]}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)


class VendorNumberListView(generics.GenericAPIView):
    def get(self, request):
        vendor_numbers = [u.profile.vendor_number for u in get_filtered_users(request)]
        # Add numbers from travel agents
        vendor_numbers.extend([])
        vendor_numbers = list(set(vendor_numbers))
        vendor_numbers.sort()
        return Response(vendor_numbers, status.HTTP_200_OK)


class PermissionMatrixView(generics.GenericAPIView):
    def get(self, request):
        return Response(PERMISSION_MATRIX, status.HTTP_200_OK)


class SettingsView(generics.GenericAPIView):
    def get(self, request):
        data = {'disable_invoicing': settings.DISABLE_INVOICING}
        return Response(data=data, status=status.HTTP_200_OK)
