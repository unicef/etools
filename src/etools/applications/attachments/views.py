from django.contrib.contenttypes.models import ContentType

from rest_framework.viewsets import ModelViewSet
from unicef_attachments.models import Attachment
from unicef_restlib.views import NestedViewSetMixin, SafeTenantViewSetMixin


class CodedAttachmentViewSet(NestedViewSetMixin, SafeTenantViewSetMixin, ModelViewSet):
    serializer_class = None
    content_model = None
    code = None
    queryset = Attachment.objects.all()

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'code': self.code,
            'content_type_id': ContentType.objects.get_for_model(self.content_model).id,
            'object_id': parent.pk,
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object())
