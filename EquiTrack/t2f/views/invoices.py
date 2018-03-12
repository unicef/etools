from __future__ import unicode_literals

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from t2f.filters import invoices
from t2f.models import Invoice
from t2f.serializers.invoices import InvoiceSerializer
from t2f.views import T2FPagePagination


class InvoiceViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    pagination_class = T2FPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (invoices.InvoiceSearchFilter,
                       invoices.InvoiceSortFilter,
                       invoices.InvoiceFilterBoxFilter)
    lookup_url_kwarg = 'invoice_pk'
