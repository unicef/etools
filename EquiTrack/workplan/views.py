
from rest_framework import mixins, viewsets

from workplan.models import Workplan
from workplan.serializers import WorkplanSerializer
from .models import Comment
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