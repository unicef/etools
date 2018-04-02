from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves import urllib_parse

from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from attachments.models import Attachment, AttachmentFlat
from attachments.serializers import (
    AttachmentFileUploadSerializer,
    AttachmentFlatSerializer,
)
from utils.common.urlresolvers import site_url


class AttachmentListView(ListAPIView):
    queryset = AttachmentFlat.objects.exclude(
        Q(attachment__file__isnull=True) | Q(attachment__file__exact=""),
        Q(attachment__hyperlink__isnull=True) | Q(attachment__hyperlink__exact="")
    )
    permission_classes = (IsAdminUser, )
    serializer_class = AttachmentFlatSerializer


class AttachmentFileView(DetailView):
    model = Attachment

    def get(self, *args, **kwargs):
        try:
            attachment = Attachment.objects.get(pk=kwargs["pk"])
        except Attachment.DoesNotExist:
            return HttpResponseNotFound(
                _("No Attachment matches the given query.")
            )
        if not attachment or not attachment.file:
            return HttpResponseNotFound(
                _("Attachment has no file or hyperlink")
            )
        url = urllib_parse.urljoin(site_url(), attachment.url)
        return HttpResponseRedirect(url)


class AttachmentCreateView(CreateAPIView):
    queryset = Attachment.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = AttachmentFileUploadSerializer

    def perform_create(self, serializer):
        self.instance = serializer.save()

    def post(self, *args, **kwargs):
        super(AttachmentCreateView, self).post(*args, **kwargs)
        return Response(
            AttachmentFlatSerializer(self.instance.denormalized.first()).data
        )


class AttachmentUpdateView(UpdateAPIView):
    queryset = Attachment.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = AttachmentFileUploadSerializer

    def perform_update(self, serializer):
        # force the updating of the uploaded by field to current user
        # this is not set when PATCH request made
        serializer.instance.uploaded_by = serializer.context["request"].user
        self.instance = serializer.save()

    def put(self, *args, **kwargs):
        super(AttachmentUpdateView, self).put(*args, **kwargs)
        return Response(
            AttachmentFlatSerializer(self.instance.denormalized.first()).data
        )

    def patch(self, *args, **kwargs):
        super(AttachmentUpdateView, self).patch(*args, **kwargs)
        return Response(
            AttachmentFlatSerializer(self.instance.denormalized.first()).data
        )
