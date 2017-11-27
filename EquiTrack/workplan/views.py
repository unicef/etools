from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from workplan.models import Label, Workplan, WorkplanProject
from workplan.serializers import (
    LabelSerializer, WorkplanProjectSerializer, WorkplanSerializer,)


class WorkplanViewSet(viewsets.ModelViewSet):
    queryset = Workplan.objects.all()
    serializer_class = WorkplanSerializer
    permission_classes = (IsAdminUser,)


class LabelViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = (IsAdminUser,)


class WorkplanProjectViewSet(viewsets.ModelViewSet):
    queryset = WorkplanProject.objects.all()
    serializer_class = WorkplanProjectSerializer
    permission_classes = (IsAdminUser,)
