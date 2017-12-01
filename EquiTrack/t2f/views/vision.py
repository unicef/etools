from __future__ import unicode_literals

from django.db.transaction import atomic
from django.http.response import HttpResponse
from django.views.generic.base import View
from rest_framework import status

from t2f.vision import InvoiceExport, InvoiceUpdateError, InvoiceUpdater


class VisionInvoiceExport(View):
    def get(self, request):
        exporter = InvoiceExport()
        xml_structure = exporter.generate_xml()
        return HttpResponse(xml_structure, content_type='application/xml')


class VisionInvoiceUpdate(View):
    def post(self, request):
        updater = InvoiceUpdater(request.body)
        try:
            with atomic():
                updater.update_invoices()
        except InvoiceUpdateError as exc:
            return HttpResponse('\n'.join(exc.errors), status=status.HTTP_400_BAD_REQUEST)
        return HttpResponse()
