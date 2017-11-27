from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from workplan.models import Label, ResultWorkplanProperty, Workplan, WorkplanProject
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

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to avoid deleting labels that are in use.
        """
        instance = self.get_object()
        if ResultWorkplanProperty.has_label(instance.id):
            return Response("Cannot delete label that is in use.", status=status.HTTP_400_BAD_REQUEST)
        return super(LabelViewSet, self).destroy(request, *args, **kwargs)


class WorkplanProjectViewSet(viewsets.ModelViewSet):
    queryset = WorkplanProject.objects.all()
    serializer_class = WorkplanProjectSerializer
    permission_classes = (IsAdminUser,)
