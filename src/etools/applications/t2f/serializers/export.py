from django.utils.translation import ugettext as _

from rest_framework import serializers

from etools.applications.t2f.models import TravelAttachment


class TravelActivityExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    traveler = serializers.CharField(source='travel.traveler.get_full_name', read_only=True)
    purpose = serializers.CharField(source='travel.purpose', read_only=True)
    section = serializers.CharField(source='travel.section.name', read_only=True)
    office = serializers.CharField(source='travel.office.name', read_only=True)
    status = serializers.CharField(source='travel.status', read_only=True)
    supervisor = serializers.CharField(source='travel.supervisor.get_full_name', read_only=True)
    trip_type = serializers.CharField(source='activity.travel_type', read_only=True)
    partner = serializers.CharField(source='activity.partner.name', read_only=True)
    partnership = serializers.CharField(source='activity.partnership.title', read_only=True)
    pd_reference = serializers.ReadOnlyField(source='activity.partnership.number', read_only=True)
    results = serializers.CharField(source='activity.result.name', read_only=True)
    locations = serializers.SerializerMethodField()
    start_date = serializers.DateField(source='travel.start_date', format='%d-%b-%Y', read_only=True)
    end_date = serializers.DateField(source='travel.end_date', format='%d-%b-%Y', read_only=True)
    is_secondary_traveler = serializers.SerializerMethodField()
    primary_traveler_name = serializers.SerializerMethodField()
    hact_visit_report = serializers.SerializerMethodField(
        label=_("HACT Programmatic visit report")
    )

    class Meta:
        fields = (
            'reference_number',
            'traveler',
            'purpose',
            'office',
            'section',
            'status',
            'supervisor',
            'trip_type',
            'partner',
            'partnership',
            'pd_reference',
            'results',
            'locations',
            'start_date',
            'end_date',
            'is_secondary_traveler',
            'primary_traveler_name',
            'hact_visit_report',
        )

    def get_locations(self, obj):
        return ', '.join([l.name for l in obj.activity.locations.all()])

    def get_is_secondary_traveler(self, obj):
        if self._is_secondary_traveler(obj):
            return 'YES'
        return ''

    def get_primary_traveler_name(self, obj):
        if self._is_secondary_traveler(obj):
            return obj.activity.primary_traveler.get_full_name()
        return ''

    def _is_secondary_traveler(self, obj):
        return obj.activity.primary_traveler != obj.travel.traveler

    def get_hact_visit_report(self, obj):
        return "Yes" if TravelAttachment.objects.filter(
            travel=obj.travel,
            type__istartswith="HACT Programme Monitoring",
        ).exists() else ""


class TravelAdminExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    traveler = serializers.CharField(source='travel.traveler.get_full_name', read_only=True)
    office = serializers.CharField(source='travel.office.name', read_only=True)
    section = serializers.CharField(source='travel.section.name', read_only=True)
    status = serializers.CharField(source='travel.status', read_only=True)
    origin = serializers.CharField()
    destination = serializers.CharField()
    departure_time = serializers.DateField(source='departure_date', format='%d-%b-%Y')
    arrival_time = serializers.DateField(source='arrival_date', format='%d-%b-%Y')
    overnight_travel = serializers.BooleanField()
    mode_of_travel = serializers.CharField()
    airline = serializers.SerializerMethodField()

    class Meta:
        fields = ('reference_number', 'traveler', 'office', 'section', 'status', 'origin', 'destination',
                  'departure_time', 'arrival_time', 'overnight_travel', 'mode_of_travel', 'airline')

    def get_airline(self, obj):
        return getattr(obj.airlines.order_by('id').last(), 'name', None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'dsa_area' not in data or not data['dsa_area']:
            data['dsa_area'] = 'NODSA'
        return data
