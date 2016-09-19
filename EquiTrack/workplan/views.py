from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from workplan.models import Workplan
from workplan.serializers import WorkplanSerializer, ResultWorkplanPropertySerializer
from .models import Comment, ResultWorkplanProperty
from .serializers import CommentSerializer


class CommentViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer



class WorkplanViewSet(mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      mixins.CreateModelMixin,
                      mixins.UpdateModelMixin,
                      viewsets.GenericViewSet):
    queryset = Workplan.objects.all()
    serializer_class = WorkplanSerializer


class ResultWorkplanPropertyViewSet(viewsets.ModelViewSet):
    """
    CRUD for ResultWorkplanProperty
    """
    queryset = ResultWorkplanProperty.objects.all()
    serializer_class = ResultWorkplanPropertySerializer
    permission_classes = (IsAdminUser,)
