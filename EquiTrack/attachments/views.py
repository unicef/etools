from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAdminUser

from attachments.models import Attachment
from attachments.serializers import AttachmentFileUploadSerializer


class FileUploadView(UpdateAPIView):
    queryset = Attachment.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = AttachmentFileUploadSerializer

    def perform_update(self, serializer):
        # force the updating of the uploaded by field to current user
        # this is not set when PATCH request made
        serializer.instance.uploaded_by = serializer.context["request"].user
        return super(FileUploadView, self).perform_update(serializer)
