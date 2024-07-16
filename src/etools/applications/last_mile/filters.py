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


class POIFilter(filters.FilterSet):
    selected_reason = filters.ChoiceFilter(
        choices=(
            (models.Transfer.DELIVERY, models.Transfer.DELIVERY),
            (models.Transfer.DISTRIBUTION, models.Transfer.DISTRIBUTION)
        ), method='selected_reason_filter')

    class Meta:
        model = models.PointOfInterest
        fields = ('selected_reason',)

    def selected_reason_filter(self, queryset, name, value):
        if value == models.Transfer.DELIVERY:
            return queryset.filter(poi_type__category='warehouse')
        elif value == models.Transfer.DISTRIBUTION:
            return queryset.exclude(poi_type__category='warehouse')
        return queryset
