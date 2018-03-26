from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves import urllib_parse

from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser

from attachments.models import Attachment, AttachmentFlat
from attachments.serializers import AttachmentSerializer
from utils.common.urlresolvers import site_url


class AttachmentListView(ListAPIView):
    queryset = AttachmentFlat.objects.exclude(
        Q(attachment__file__isnull=True) | Q(attachment__file__exact=""),
        Q(attachment__hyperlink__isnull=True) | Q(attachment__hyperlink__exact="")
    )
    permission_classes = (IsAdminUser, )
    serializer_class = AttachmentSerializer


class AttachmentFileView(DetailView):
    model = Attachment

    def get(self, *args, **kwargs):
        try:
            attachment = Attachment.objects.get(pk=kwargs["pk"])
        except Attachment.DoesNotExist:
            return HttpResponseNotFound(
                _("No Attachment matches the given query.")
            )
        if attachment.url == "None":
            return HttpResponseNotFound(
                _("Attachment has no file or hyperlink")
            )
        url = urllib_parse.urljoin(site_url(), attachment.url)
        return HttpResponseRedirect(url)
