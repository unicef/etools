from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.http import Http404

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins
from unicef_restlib.views import MultiSerializerViewSetMixin

from etools.applications.comments.export.renderers import CommentCSVRenderer
from etools.applications.comments.export.serializers import CommentCSVSerializer
from etools.applications.comments.models import Comment
from etools.applications.comments.permissions import IsCommentAuthor
from etools.applications.comments.serializers import CommentEditSerializer, CommentSerializer, NewCommentSerializer
from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction


class CommentsViewSet(
    MultiSerializerViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = CommentSerializer
    queryset = Comment.objects.select_related('user').prefetch_related('users_related')
    queryset = queryset.order_by('created', 'related_to')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & IsCommentAuthor)
    ]
    serializer_action_classes = {
        'create': NewCommentSerializer,
        'update': CommentEditSerializer,
        'partial_update': CommentEditSerializer,
    }

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

    @action(detail=True, methods=['post'])
    def resolve(self, request, *args, **kwargs):
        comment = self.get_object()
        self.check_object_permissions(self.request, comment)

        try:
            comment.resolve()
        except DjangoValidationError as ex:
            raise ValidationError({'non_field_errors': ex.messages})

        serializer = self.get_serializer(comment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def delete(self, request, *args, **kwargs):
        comment = self.get_object()
        self.check_object_permissions(self.request, comment)

        try:
            comment.remove()
        except DjangoValidationError as ex:
            raise ValidationError({'non_field_errors': ex.messages})

        serializer = self.get_serializer(comment)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='csv', url_name='export_csv', renderer_classes=[CommentCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        instance = self.get_related_instance()
        instance_identifier = getattr(instance, 'reference_number', str(instance))
        serializer = CommentCSVSerializer(instance=self.get_queryset().exclude(state=Comment.STATES.deleted), many=True)

        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}.csv'.format(instance_identifier)
        })
