from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from workplan.models import Workplan
from workplan.serializers import (
    WorkplanSerializer,)


class WorkplanViewSet(viewsets.ModelViewSet):
    queryset = Workplan.objects.all()
    serializer_class = WorkplanSerializer
    permission_classes = (IsAdminUser,)
