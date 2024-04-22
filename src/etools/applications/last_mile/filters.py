from django_filters import rest_framework as filters

from etools.applications.last_mile import models


class TransferFilter(filters.FilterSet):
    status__in = filters.BaseInFilter(field_name="status", lookup_expr="")
    transfer_type__in = filters.BaseInFilter(field_name="transfer_type")
    transfer_subtype__in = filters.BaseInFilter(field_name="transfer_subtype")

    class Meta:
        model = models.Transfer
        fields = {
            'status': ['exact', 'in'],
            'transfer_type': ['exact', 'in'],
            'transfer_subtype': ['exact', 'in']
        }
