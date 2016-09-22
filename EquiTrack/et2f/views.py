
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import Travel
from .serializers import TravelSerializer


class TravelViewSet(viewsets.ModelViewSet):
    queryset = Travel.objects.all()
    model = Travel
    serializer_class = TravelSerializer
    permission_classes = (IsAdminUser,)