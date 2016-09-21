from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from .models import Workplan, Comment, ResultWorkplanProperty, WorkplanProject, Label
from .serializers import CommentSerializer, WorkplanSerializer, ResultWorkplanPropertySerializer,\
    WorkplanProjectSerializer, LabelSerializer
from .tasks import notify_comment_tagged_users


class TaggedNotificationMixin(object):

    def perform_update(self, serializer):
        # Caches the original set of tagged users on the instance to be able to
        # determine new ones after update.
        comment = self.get_object()
        tagged_users_old = {x.id for x in comment.tagged_users.all()}
        instance = serializer.save()
        tagged_users_new = {x.id for x in instance.tagged_users.all()}
        # Compare newly added to the old set
        users_to_notify = list(tagged_users_new - tagged_users_old)

        # Trigger notification
        if users_to_notify:
            notify_comment_tagged_users.delay(users_to_notify, instance.id)

    def perform_create(self, serializer):
        instance = serializer.save()
        tagged_users_new = {x.id for x in instance.tagged_users.all()}

        # Trigger notification
        if tagged_users_new:
            notify_comment_tagged_users.delay(tagged_users_new, instance.id)


class CommentViewSet(TaggedNotificationMixin, viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
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
