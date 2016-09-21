
from rest_framework import mixins, viewsets

from .models import Comment
from .serializers import CommentSerializer
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
        users_to_notify = list(tagged_users_new & set(tagged_users_new ^ tagged_users_old))

        # Trigger notification
        notify_comment_tagged_users.delay(users_to_notify, instance.id)

    def perform_create(self, serializer):
        instance = serializer.save()
        tagged_users_new = {x.id for x in instance.tagged_users.all()}

        # Trigger notification
        notify_comment_tagged_users.delay(tagged_users_new, instance.id)


class CommentViewSet(TaggedNotificationMixin,
                     mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
