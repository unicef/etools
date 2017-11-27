from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from workplan.models import Workplan, WorkplanProject
from workplan.serializers import (
    WorkplanProjectSerializer, WorkplanSerializer,)


class WorkplanViewSet(viewsets.ModelViewSet):
    queryset = Workplan.objects.all()
    serializer_class = WorkplanSerializer
    permission_classes = (IsAdminUser,)


class WorkplanProjectViewSet(viewsets.ModelViewSet):
    queryset = WorkplanProject.objects.all()
    serializer_class = WorkplanProjectSerializer
    permission_classes = (IsAdminUser,)
