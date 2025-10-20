from django.contrib.auth import get_user_model
from django.db.models import CharField, F, Func, Q

from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES

from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES
from etools.applications.last_mile.models import Item, PointOfInterest, Transfer, TransferHistory
from etools.applications.locations.models import Location


class OrCharFilter(filters.CharFilter):
    def __init__(self, *args, field_names, **kwargs):
        self.field_names = field_names
        kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        q_objects = Q()
        for field_name in self.field_names:
            lookup = {f"{field_name}__{self.lookup_expr}": value}
            q_objects |= Q(**lookup)

        return qs.filter(q_objects)


class OrCharFilterWithItemsCheck(filters.CharFilter):
    def __init__(self, *args, field_names, **kwargs):
        self.field_names = field_names
        kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        q_objects = Q()
        for field_name in self.field_names:
            lookup = {f"{field_name}__{self.lookup_expr}": value}

            if field_name.startswith('origin_transfer'):
                items_check = Q(origin_transfer__items__isnull=False)
            elif field_name.startswith('transfers'):
                items_check = Q(transfers__items__isnull=False)
            else:
                items_check = Q()

            q_objects |= (Q(**lookup) & items_check)

        return qs.filter(q_objects).distinct()


class UserFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    organization_name = filters.CharFilter(field_name="profile__organization__name", lookup_expr="icontains")
    organization_vendor_number = filters.CharFilter(field_name="profile__organization__vendor_number", lookup_expr="icontains")
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
    secondary_type = filters.CharFilter(field_name="secondary_type__name", lookup_expr="icontains")
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
        fields = ('name', 'p_code', 'primary_type', 'is_active', 'secondary_type')


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
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    alert_type = filters.CharFilter(method='filter_alert_type', label='Alert Type')

    def filter_alert_type(self, queryset, name, value):
        mapped_groups = [
            group_name for group_name, alert_value in ALERT_TYPES.items()
            if value.lower() in alert_value.lower()
        ]
        if mapped_groups:
            return queryset.filter(realms__group__name__in=mapped_groups)
        return queryset.filter(realms__group__name__icontains=value)

    class Meta:
        model = get_user_model()
        fields = ('email',)


class TransferHistoryFilter(filters.FilterSet):
    unicef_release_order = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__unicef_release_order', 'transfers__unicef_release_order'],
        lookup_expr='icontains',
        label='UNICEF Release Order'
    )
    transfer_name = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__name', 'transfers__name'],
        lookup_expr='icontains',
        label='Transfer Name'
    )
    transfer_type = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__transfer_type', 'transfers__transfer_type'],
        lookup_expr='icontains',
        label='Transfer Type'
    )
    status = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__status', 'transfers__status'],
        lookup_expr='icontains',
        label='Status'
    )
    partner_organization = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__partner_organization__organization__name', 'transfers__partner_organization__organization__name'],
        lookup_expr='icontains',
        label='Partner Organization'
    )
    origin_point = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__origin_point__name', 'transfers__origin_point__name'],
        lookup_expr='icontains',
        label='Origin Point'
    )
    destination_point = OrCharFilterWithItemsCheck(
        field_names=['origin_transfer__destination_point__name', 'transfers__destination_point__name'],
        lookup_expr='icontains',
        label='Destination Point'
    )

    @property
    def qs(self):
        queryset = super().qs
        queryset = queryset.select_related(
            'origin_transfer',
            'origin_transfer__partner_organization__organization',
            'origin_transfer__origin_point',
            'origin_transfer__destination_point'
        ).prefetch_related(
            'transfers',
            'transfers__partner_organization__organization',
            'transfers__origin_point',
            'transfers__destination_point',
            'transfers__items',
            'origin_transfer__items'
        ).distinct()
        return queryset

    class Meta:
        model = TransferHistory
        fields = []


class TransferEvidenceFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    transfer_type = filters.CharFilter(field_name="transfer_type", lookup_expr="icontains")
    unicef_release_order = filters.CharFilter(field_name="unicef_release_order", lookup_expr="icontains")
    status = filters.CharFilter(field_name="status", lookup_expr="icontains")
    partner_organization = filters.CharFilter(field_name="partner_organization__organization__name", lookup_expr="icontains")
    from_partner_organization = OrCharFilter(
        field_names=["from_partner_organization__organization__name", "partner_organization__organization__name"],
        lookup_expr="icontains",
        label="Partner Organization"
    )
    recipient_partner_organization = filters.CharFilter(field_name="recipient_partner_organization__organization__name", lookup_expr="icontains")
    origin_point = filters.CharFilter(field_name="origin_point__name", lookup_expr="icontains")
    destination_point = filters.CharFilter(field_name="destination_point__name", lookup_expr="icontains")

    class Meta:
        model = Transfer
        fields = ('name', 'transfer_type')


class ItemFilter(filters.FilterSet):
    poi_id = filters.NumberFilter(field_name='transfer__destination_point_id', lookup_expr='exact')
    description = filters.CharFilter(method='filter_mapped_description', label='description')
    material_description = filters.CharFilter(field_name="material__short_description", lookup_expr="icontains")
    material_number = filters.CharFilter(field_name="material__number", lookup_expr="icontains")
    quantity = filters.NumberFilter(field_name='quantity', lookup_expr='exact')
    uom = filters.CharFilter(field_name="uom", lookup_expr="icontains")
    batch_id = filters.CharFilter(field_name="batch_id", lookup_expr="icontains")

    class Meta:
        model = Item
        fields = [
            'poi_id',
            'description',
            'material_description',
            'material_number',
            'quantity',
            'uom',
            'batch_id'
        ]

    def filter_mapped_description(self, queryset, name, value):
        return queryset.filter(
            Q(mapped_description__icontains=value) |
            Q(material__short_description__icontains=value)
        )
