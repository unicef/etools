from copy import copy

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from unicef_attachments.models import Attachment, AttachmentLink
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.field_monitoring.fm_settings.serializers import LinkedAttachmentBaseSerializer


class FMBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class AttachmentFileTypesViewMixin:
    @action(detail=False, methods=['GET'], url_path='file-types', url_name='file-types')
    def file_types(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        declared_fields = serializer_class._declared_fields
        if 'file_type' not in declared_fields:
            raise Http404

        return Response(data=declared_fields['file_type'].queryset.filter(~Q(label__in=["SOP", "Other"])).values('id', 'label'))


class LinkedAttachmentsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    AttachmentFileTypesViewMixin,
    ModelViewSet,
):
    queryset = Attachment.objects.select_related('uploaded_by')
    serializer_class = LinkedAttachmentBaseSerializer
    attachment_code = ''  # fill `code` field in attachment to deal with coded generics
    filter_backends = (DjangoFilterBackend,)
    related_model = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.attachment_code:
            queryset = queryset.filter(code=self.attachment_code)

        return queryset

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

    def update_attachment(self, pk, object_id, content_type, **kwargs):
        generic_kwargs = {
            'object_id': object_id,
            'content_type': content_type,
        }
        attachment_kwargs = copy(generic_kwargs)
        attachment_kwargs.update(kwargs)
        Attachment.objects.filter(pk=pk).update(**attachment_kwargs)
        # keep attachment link in sync
        AttachmentLink.objects.get_or_create(attachment_id=pk, **generic_kwargs)

    def set_attachments(self, data):
        parent_instance = self.get_parent_object()

        content_type = ContentType.objects.get_for_model(self.related_model)
        current = list(self.filter_queryset(self.get_queryset()))
        used = []
        for attachment_data in data:
            pk = attachment_data['id']
            current = [a for a in current if a.pk != pk]
            self.update_attachment(
                pk, parent_instance.pk, content_type,
                file_type=attachment_data.get("file_type", None),
                code=self.attachment_code,
            )
            used.append(pk)

        for attachment in current:
            attachment.delete()

        return Attachment.objects.filter(pk__in=used)

    @action(detail=False, methods=['PUT'], url_name='bulk_update', url_path='bulk-update')
    def bulk_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True, partial=False)
        serializer.is_valid(raise_exception=True)
        attachments = self.set_attachments(serializer.validated_data)
        return Response(self.get_serializer(instance=attachments, many=True).data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        instead of standard create we have an instance, so we should link existing one.
        the easiest way is to handle similar to update
        """
        instance = get_object_or_404(Attachment.objects, pk=request.data.get('id'))
        serializer = self.get_serializer(data=request.data, instance=instance, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        attachment_data = serializer.validated_data
        pk = attachment_data['id']

        self.update_attachment(
            pk, self.get_parent_object().pk,
            ContentType.objects.get_for_model(self.related_model),
            file_type=attachment_data.get("file_type", None),
            code=self.attachment_code,
        )

    def perform_update(self, serializer):
        attachment_data = serializer.validated_data
        pk = self.get_object().pk

        self.update_attachment(
            pk, self.get_parent_object().pk,
            ContentType.objects.get_for_model(self.related_model),
            file_type=attachment_data.get("file_type", None),
            code=self.attachment_code,
        )


class BulkUpdateMixin:
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """
        bulk update action. id's are required to correctly identify instances to update
        """
        if not isinstance(request.data, list):
            raise HttpResponseBadRequest

        objects_to_update = self.filter_queryset(self.get_queryset()).filter(**{
            'id__in': [d['id'] for d in request.data],
        })
        data_by_id = {i.pop('id'): i for i in request.data}

        updated_objects = []

        for obj in objects_to_update:
            serializer = self.get_serializer(instance=obj, data=data_by_id[obj.id], partial=True)
            serializer.is_valid(raise_exception=True)
            updated_objects.append(serializer.save())

        return Response(self.get_serializer(instance=updated_objects, many=True).data, status=status.HTTP_200_OK)
