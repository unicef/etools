from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import Workplan, Comment, ResultWorkplanProperty, WorkplanProject
from .serializers import CommentSerializer, WorkplanSerializer, ResultWorkplanPropertySerializer,\
    WorkplanProjectSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAdminUser,)


class WorkplanViewSet(viewsets.ModelViewSet):
    queryset = Workplan.objects.all()
    serializer_class = WorkplanSerializer
    permission_classes = (IsAdminUser,)


class ResultWorkplanPropertyViewSet(viewsets.ModelViewSet):
    """
    CRUD for ResultWorkplanProperty
    """
    queryset = ResultWorkplanProperty.objects.all()
    serializer_class = ResultWorkplanPropertySerializer
    permission_classes = (IsAdminUser,)


class WorkplanProjectViewSet(viewsets.ModelViewSet):
    queryset = WorkplanProject.objects.all()
    serializer_class = WorkplanProjectSerializer
    permission_classes = (IsAdminUser,)