from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAdminUser

from attachments.models import Attachment
from attachments.serializers import AttachmentFileUploadSerializer


class FileUploadView(UpdateAPIView):
    queryset = Attachment.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = AttachmentFileUploadSerializer
