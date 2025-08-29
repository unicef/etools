from django.contrib.auth import get_user_model

from django_filters import rest_framework as filters


class UserFilter(filters.FilterSet):
    workspace = filters.CharFilter(method='filter_workspace', label='workspace')
    role = filters.CharFilter(method='filter_role', label='role')
    vendor_number = filters.CharFilter(field_name='profile__organization__vendor_number', lookup_expr='icontains')

    class Meta:
        model = get_user_model()
        fields = ['workspace', 'role', 'vendor_number']

    def filter_workspace(self, queryset, name, value):
        return queryset.filter(
            realms__country__name__icontains=value,
            realms__is_active=True,
            is_active=True
        ).distinct()

    def filter_role(self, queryset, name, value):
        return queryset.filter(
            realms__group__name__icontains=value,
            realms__is_active=True,
            is_active=True
        ).distinct()
