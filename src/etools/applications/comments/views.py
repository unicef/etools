from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, mixins
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.comments.models import Comment
from etools.applications.comments.permissions import IsCommentAuthor
from etools.applications.comments.serializers import CommentSerializer
from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction


class CommentsViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    serializer_class = CommentSerializer
    queryset = Comment.objects.select_related('user').prefetch_related('users_related')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & IsCommentAuthor)
        # todo: refine permissions
    ]

    def get_related_content_type(self):
        return get_object_or_404(ContentType, app_label=self.kwargs['related_app'], model=self.kwargs['related_model'])

    def get_related_instance(self):
        try:
            return self.get_related_content_type().get_object_for_this_type(id=self.kwargs['related_id'])
        except ObjectDoesNotExist:
            raise Http404

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            instance_related_ct=self.get_related_content_type(),
            instance_related_id=self.kwargs['related_id']
        )
        return queryset

    def perform_create(self, serializer):
        return serializer.save(instance_related=self.get_related_instance())

    # todo: add action to mark as resolved
