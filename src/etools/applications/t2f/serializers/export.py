from django.utils.translation import ugettext as _

from rest_framework import serializers

from etools.applications.t2f.models import TravelAttachment


class YesOrEmptyField(serializers.BooleanField):
    def to_representation(self, value):
        value = super().to_representation(value)
        if value:
            return _('Yes')
        return ''


class YesOrNoField(serializers.BooleanField):
    def to_representation(self, value):
        value = super().to_representation(value)
        if value:
            return _('Yes')
        return _('No')


class TravelActivityExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    traveler = serializers.CharField(source='travel.traveler.get_full_name', read_only=True)
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
    start_date = serializers.DateTimeField(source='travel.start_date', format='%d-%b-%Y', read_only=True)
    end_date = serializers.DateTimeField(source='travel.end_date', format='%d-%b-%Y', read_only=True)
    is_secondary_traveler = serializers.SerializerMethodField()
    primary_traveler_name = serializers.SerializerMethodField()
    hact_visit_report = serializers.SerializerMethodField(
        label=_("HACT Programmatic visit report")
    )

    class Meta:
        fields = (
            'reference_number',
            'traveler',
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
            type="HACT Programme Monitoring",
        ).exists() else "No"


class FinanceExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField()
    traveler = serializers.CharField(source='traveler.get_full_name', read_only=True)
    office = serializers.CharField(source='office.name', read_only=True)
    section = serializers.CharField(source='section.name', read_only=True)
    status = serializers.CharField()
    supervisor = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    start_date = serializers.DateTimeField(format='%d-%b-%Y')
    end_date = serializers.DateTimeField(format='%d-%b-%Y')
    purpose_of_travel = serializers.CharField(source='purpose')
    mode_of_travel = serializers.SerializerMethodField()
    international_travel = YesOrNoField()
    require_ta = YesOrNoField(source='ta_required')
    dsa_total = serializers.DecimalField(source='cost_summary.dsa_total', max_digits=20, decimal_places=2,
                                         read_only=True)
    expense_total = serializers.SerializerMethodField()
    deductions_total = serializers.DecimalField(
        source='cost_summary.deductions_total', max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        fields = ('reference_number', 'traveler', 'office', 'section', 'status', 'supervisor', 'start_date',
                  'end_date', 'purpose_of_travel', 'mode_of_travel', 'international_travel', 'require_ta', 'dsa_total',
                  'expense_total', 'deductions_total')

    def get_mode_of_travel(self, obj):
        if obj.mode_of_travel:
            return ', '.join(obj.mode_of_travel)
        return ''

    def get_expense_total(self, obj):
        ret = []
        for expense in obj.cost_summary['expenses_total']:
            if not expense['currency']:
                continue

            ret.append('{amount:.{currency.decimal_places}f} {currency.code}'.format(amount=expense['amount'],
                                                                                     currency=expense['currency']))
        return '+'.join(ret)


class TravelAdminExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    traveler = serializers.CharField(source='travel.traveler.get_full_name', read_only=True)
    office = serializers.CharField(source='travel.office.name', read_only=True)
    section = serializers.CharField(source='travel.section.name', read_only=True)
    status = serializers.CharField(source='travel.status', read_only=True)
    origin = serializers.CharField()
    destination = serializers.CharField()
    departure_time = serializers.DateTimeField(source='departure_date', format='%d-%b-%Y %I:%M %p')
    arrival_time = serializers.DateTimeField(source='arrival_date', format='%d-%b-%Y %I:%M %p')
    dsa_area = serializers.CharField(source='dsa_region.area_code', read_only=True)
    overnight_travel = YesOrEmptyField()
    mode_of_travel = serializers.CharField()
    airline = serializers.SerializerMethodField()

    class Meta:
        fields = ('reference_number', 'traveler', 'office', 'section', 'status', 'origin', 'destination',
                  'departure_time', 'arrival_time', 'dsa_area', 'overnight_travel', 'mode_of_travel', 'airline')

    def get_airline(self, obj):
        return getattr(obj.airlines.order_by('id').last(), 'name', None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'dsa_area' not in data or not data['dsa_area']:
            data['dsa_area'] = 'NODSA'
        return data
