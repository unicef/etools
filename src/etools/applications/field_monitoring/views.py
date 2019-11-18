from django.contrib.contenttypes.models import ContentType
from django.http import Http404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_bulk import BulkDestroyModelMixin, BulkUpdateModelMixin
from unicef_attachments.models import Attachment, AttachmentLink
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.field_monitoring.fm_settings.serializers import LinkedAttachmentBulkSerializer
from etools.applications.permissions2.metadata import BaseMetadata


class FMBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = BaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class AttachmentFileTypesViewMixin:
    @action(detail=False, methods=['GET'], url_path='file-types', url_name='file-types')
    def file_types(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        declared_fields = serializer_class._declared_fields
        if 'file_type' not in declared_fields:
            raise Http404

        return Response(data=dict(declared_fields['file_type'].queryset.values_list('id', 'label')))


class LinkedAttachmentsViewSet(
    FMBaseViewSet,
    AttachmentFileTypesViewMixin,
    ListModelMixin,
    RetrieveModelMixin,
    BulkUpdateModelMixin,
    UpdateModelMixin,
    BulkDestroyModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = Attachment.objects.all()
    serializer_class = LinkedAttachmentBulkSerializer
    attachment_code = ''  # fill `code` field in attachment to deal with coded generics
    filter_backends = (DjangoFilterBackend,)
    filter_fields = {'id': ['in']}

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.attachment_code:
            queryset = queryset.filter(code=self.attachment_code)

        return queryset

    def perform_linking(self, serializer):
        # set code for instance
        if self.attachment_code:
            instances = serializer.save(code=self.attachment_code)
        else:
            instances = serializer.save()

        # now link updated instances
        for instance in instances:
            AttachmentLink.objects.create(attachment=instance)

    @action(detail=False, methods=['POST'], url_path='link', url_name='link')
    def link_attachments(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            Attachment.objects.filter(pk__in=[a['id'] for a in request.data if a.get('id')]),
            data=request.data,
            many=True,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_linking(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        instance.content_object = None
        instance.save()

        # unlink instance
        instance.links.all().delete()

    def allow_bulk_destroy(self, qs, filtered):
        allow = super().allow_bulk_destroy(qs, filtered)
        if not allow:
            return False

        # assure all instances are editable by user before removing
        for instance in filtered:
            self.check_object_permissions(self.request, instance)

        return True


class NestedLinkedAttachmentsViewSet(NestedViewSetMixin, LinkedAttachmentsViewSet):
    related_model = None

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        content_type = ContentType.objects.get_for_model(self.related_model)

        filter_kwargs = {
            'content_type': content_type.id,
            'object_id': parent.pk,
        }
        if self.attachment_code:
            filter_kwargs['code'] = self.attachment_code
        return filter_kwargs

    def _get_parent_filters(self):
        # too deep inheritance is not supported in case of generic relations, so just use parent (content object)
        return self.get_parent_filter()

    def perform_linking(self, serializer):
        parent = self.get_parent_object()
        # set content_object and code for instance
        instances = serializer.save(content_object=parent, code=self.attachment_code)

        # now link updated instances
        for instance in instances:
            AttachmentLink.objects.create(attachment=instance, content_object=parent)
