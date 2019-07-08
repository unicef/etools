from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from unicef_attachments.models import Attachment
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.permissions2.metadata import BaseMetadata


class FMBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = BaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class FMBaseAttachmentsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet
):
    metadata_class = BaseMetadata
    queryset = Attachment.objects.all()
    related_model = None

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'content_type_id': ContentType.objects.get_for_model(self.related_model).id,
            'object_id': parent.pk,
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object())
