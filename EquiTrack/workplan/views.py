from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from workplan.models import Workplan, Comment, ResultWorkplanProperty, WorkplanProject, Label, Milestone
from workplan.serializers import CommentSerializer, WorkplanSerializer,\
    WorkplanProjectSerializer, LabelSerializer, MilestoneSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAdminUser,)


class MilestoneViewSet(viewsets.ModelViewSet):
    """
    CRUD api for Milestones
    """
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = (IsAdminUser,)


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
