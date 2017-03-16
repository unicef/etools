from __future__ import unicode_literals


from t2f.filters import BaseSearchFilter, BaseSortFilter, BaseFilterBoxFilter
from t2f.serializers.filters.invoices import InvoiceSortFilterSerializer, InvoiceFilterBoxSerializer


class InvoiceSearchFilter(BaseSearchFilter):
    _search_fields = ('reference_number', 'vendor_number', 'travel__reference_number', 'vision_fi_id')


class InvoiceSortFilter(BaseSortFilter):
    serializer_class = InvoiceSortFilterSerializer


class InvoiceFilterBoxFilter(BaseFilterBoxFilter):
    serializer_class = InvoiceFilterBoxSerializer
