from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from workplan.models import Workplan
from workplan.serializers import WorkplanSerializer, ResultWorkplanPropertySerializer
from .models import Comment, ResultWorkplanProperty, Label
from .serializers import CommentSerializer, LabelSerializer


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


class ResultWorkplanPropertyViewSet(viewsets.ModelViewSet):
    """
    CRUD for ResultWorkplanProperty
    """
    queryset = ResultWorkplanProperty.objects.all()
    serializer_class = ResultWorkplanPropertySerializer
    permission_classes = (IsAdminUser,)
