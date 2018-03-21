from six.moves import urllib_parse

from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from attachments.models import ATTACHMENT_CACHE_KEY_FORMAT, Attachment
from attachments.serializers import AttachmentSerializer
from utils.common.urlresolvers import site_url


class AttachmentListView(ListAPIView):
    queryset = Attachment.objects.exclude(
        Q(file__isnull=True) | Q(file__exact=""),
        Q(hyperlink__isnull=True) | Q(hyperlink__exact="")
    )
    permission_classes = (IsAdminUser, )
    serializer_class = AttachmentSerializer

    def get(self, *args, **kwargs):
        cache_key = ATTACHMENT_CACHE_KEY_FORMAT.format(connection.schema_name)
        data = cache.get(cache_key)
        if data is None:
            response = super(AttachmentListView, self).get(*args, **kwargs)
            data = response.data
            cache.set(cache_key, response.data)
        return Response(data)


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
