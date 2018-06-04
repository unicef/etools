
from etools.applications.t2f.filters import BaseFilterBoxFilter, BaseSearchFilter, BaseSortFilter
from etools.applications.t2f.serializers.filters.invoices import (InvoiceFilterBoxSerializer,
                                                                  InvoiceSortFilterSerializer,)


class InvoiceSearchFilter(BaseSearchFilter):
    _search_fields = ('reference_number', 'vendor_number', 'travel__reference_number', 'vision_fi_id')


class InvoiceSortFilter(BaseSortFilter):
    serializer_class = InvoiceSortFilterSerializer


class InvoiceFilterBoxFilter(BaseFilterBoxFilter):
    serializer_class = InvoiceFilterBoxSerializer
