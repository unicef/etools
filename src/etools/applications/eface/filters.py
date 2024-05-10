from django_filters import rest_framework as filters

from etools.applications.eface.models import EFaceForm


class EFaceFormFilterSet(filters.FilterSet):
    class Meta:
        model = EFaceForm
        fields = {
            'created': ['gte', 'lte'],
            'status': ['exact', 'in'],
        }
