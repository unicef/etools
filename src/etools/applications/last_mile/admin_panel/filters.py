from django.contrib.auth import get_user_model
from django.db.models import CharField, F, Func, Q

from django_filters import rest_framework as filters

from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES
from etools.applications.last_mile.models import PointOfInterest, TransferHistory
from etools.applications.locations.models import Location
from etools.applications.users.models import Realm


class UserFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    organization_name = filters.CharFilter(field_name="profile__organization__name", lookup_expr="icontains")
    country_name = filters.CharFilter(field_name="profile__country__name", lookup_expr="icontains")
    is_active = filters.BooleanFilter(field_name="is_active")
    profile_status = filters.CharFilter(field_name="last_mile_profile__status", lookup_expr="icontains")

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email', 'is_active')


class LocationsFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    p_code = filters.CharFilter(field_name="p_code", lookup_expr="icontains")
    district = filters.CharFilter(method='filter_district', label='District')
    region = filters.CharFilter(method='filter_region', label='Region')
    country = filters.CharFilter(method='filter_country', label='Country')
    partner_organization = filters.CharFilter(method='filter_partner_organization', label='Partner Organization Name/Number')
    primary_type = filters.CharFilter(field_name="poi_type__name", lookup_expr="icontains")
    is_active = filters.BooleanFilter(field_name="is_active")
    latitude = filters.CharFilter(method='filter_latitude', label='Latitude')
    longitude = filters.CharFilter(method='filter_longitude', label='Longitude')

    def filter_by_admin_level(self, queryset, name, value, admin_level):
        locations = Location.objects.filter(
            admin_level=admin_level,
            name__icontains=value
        )
        if not locations.exists():
            return queryset.none()

        q_filter = Q()
        for loc in locations:
            q_filter |= Q(
                parent__tree_id=loc.tree_id,
                parent__lft__gte=loc.lft,
                parent__rght__lte=loc.rght,
            )
        return queryset.filter(q_filter)

    def filter_district(self, queryset, name, value):
        return self.filter_by_admin_level(queryset, name, value, Location.THIRD_ADMIN_LEVEL)

    def filter_region(self, queryset, name, value):
        return self.filter_by_admin_level(queryset, name, value, Location.SECOND_ADMIN_LEVEL)

    def filter_country(self, queryset, name, value):
        return self.filter_by_admin_level(queryset, name, value, Location.FIRST_ADMIN_LEVEL)

    def filter_partner_organization(self, queryset, name, value):
        return queryset.filter(
            Q(partner_organizations__organization__name__icontains=value) |
            Q(partner_organizations__organization__vendor_number__icontains=value)
        ).distinct()

    def filter_latitude(self, queryset, name, value):
        queryset = queryset.annotate(
            latitude=Func(F('point'), function='ST_Y', output_field=CharField())
        )
        return queryset.filter(latitude__startswith=value)

    def filter_longitude(self, queryset, name, value):
        queryset = queryset.annotate(
            longitude=Func(F('point'), function='ST_X', output_field=CharField())
        )
        return queryset.filter(longitude__startswith=value)

    class Meta:
        model = PointOfInterest
        fields = ('name', 'p_code', 'primary_type', 'is_active')


class UserLocationsFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    organization_name = filters.CharFilter(field_name="profile__organization__name", lookup_expr="icontains")
    locations_name = filters.CharFilter(method='filter_locations_name', label='Location Name')

    def filter_locations_name(self, queryset, name, value):
        return queryset.filter(profile__organization__partner__points_of_interest__name__icontains=value)

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')


class AlertNotificationFilter(filters.FilterSet):
    email = filters.CharFilter(field_name="user__email", lookup_expr="icontains")
    alert_type = filters.CharFilter(method='filter_alert_type', label='Alert Type')

    def filter_alert_type(self, queryset, name, value):
        mapped_groups = [
            group_name for group_name, alert_value in ALERT_TYPES.items()
            if value.lower() in alert_value.lower()
        ]
        if mapped_groups:
            return queryset.filter(group__name__in=mapped_groups)
        return queryset.filter(group__name__icontains=value)

    class Meta:
        model = Realm
        fields = ('email',)


class TransferHistoryFilter(filters.FilterSet):
    unicef_release_order = filters.CharFilter(
        field_name='unicef_release_order', lookup_expr='icontains', label='UNICEF Release Order'
    )
    transfer_name = filters.CharFilter(
        field_name='transfer_name', lookup_expr='icontains', label='Transfer Name'
    )
    transfer_type = filters.CharFilter(
        field_name='transfer_type', lookup_expr='icontains', label='Transfer Type'
    )
    status = filters.CharFilter(
        field_name='status', lookup_expr='icontains', label='Status'
    )
    partner_organization = filters.CharFilter(
        field_name='partner_organization', lookup_expr='icontains', label='Partner Organization'
    )
    origin_point = filters.CharFilter(
        field_name='origin_point', lookup_expr='icontains', label='Origin Point'
    )
    destination_point = filters.CharFilter(
        field_name='destination_point', lookup_expr='icontains', label='Destination Point'
    )

    class Meta:
        model = TransferHistory
        fields = []
