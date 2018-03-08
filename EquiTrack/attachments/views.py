from django.db.models import Q
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAdminUser

from attachments.models import Attachment
from attachments.serializers import (
    AttachmentFileUploadSerializer,
    AttachmentSerializer,
)


class FileUploadView(UpdateAPIView):
    queryset = Attachment.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = AttachmentFileUploadSerializer

    def perform_update(self, serializer):
        # force the updating of the uploaded by field to current user
        # this is not set when PATCH request made
        serializer.instance.uploaded_by = serializer.context["request"].user
        return super(FileUploadView, self).perform_update(serializer)


class AttachmentListView(ListAPIView):
    queryset = Attachment.objects.exclude(
        Q(file__isnull=True) | Q(file__exact=""),
        Q(hyperlink__isnull=True) | Q(hyperlink__exact="")
    )
    permission_classes = (IsAdminUser, )
    serializer_class = AttachmentSerializer

    def get_queryset(self):
        file_type = self.request.query_params.getlist("file_type")
        if file_type:
            self.queryset = self.queryset.filter(file_type__pk__in=file_type)
        before = self.request.query_params.get("before")
        if before:
            self.queryset = self.queryset.filter(modified__lte=before)
        after = self.request.query_params.get("after")
        if after:
            self.queryset = self.queryset.filter(modified__gte=after)
        uploaded_by = self.request.query_params.getlist("uploaded_by")
        if uploaded_by:
            self.queryset = self.queryset.filter(
                uploaded_by__pk__in=uploaded_by
            )
        return self.queryset.all()
