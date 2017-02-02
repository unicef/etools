from __future__ import unicode_literals

from rest_framework import serializers

from t2f.serializers import ActionPointSerializer
from t2f.serializers.filters import SortFilterSerializer


class InvoiceSortFilterSerializer(SortFilterSerializer):
    _SORTABLE_FIELDS = tuple(ActionPointSerializer.Meta.fields)


class InvoiceFilterBoxSerializer(serializers.Serializer):
    f_vendor_number = serializers.CharField(source='vendor_number', required=False)
    f_status = serializers.CharField(source='status', required=False)
