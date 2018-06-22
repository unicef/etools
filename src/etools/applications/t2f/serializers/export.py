
from django.utils.translation import ugettext

from rest_framework import serializers


class YesOrEmptyField(serializers.BooleanField):
    def to_representation(self, value):
        value = super(YesOrEmptyField, self).to_representation(value)
        if value:
            return ugettext('Yes')
        return ''


class YesOrNoField(serializers.BooleanField):
    def to_representation(self, value):
        value = super(YesOrNoField, self).to_representation(value)
        if value:
            return ugettext('Yes')
        return ugettext('No')


class TravelActivityExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    traveler = serializers.CharField(source='travel.traveler.get_full_name', read_only=True)
    section = serializers.CharField(source='travel.sector.name', read_only=True)
    office = serializers.CharField(source='travel.office.name', read_only=True)
    status = serializers.CharField(source='travel.status', read_only=True)
    trip_type = serializers.CharField(source='activity.travel_type', read_only=True)
    partner = serializers.CharField(source='activity.partner.name', read_only=True)
    partnership = serializers.CharField(source='activity.partnership.title', read_only=True)
    results = serializers.CharField(source='activity.result.name', read_only=True)
    locations = serializers.SerializerMethodField()
    start_date = serializers.DateTimeField(source='travel.start_date', format='%d-%b-%Y', read_only=True)
    end_date = serializers.DateTimeField(source='travel.end_date', format='%d-%b-%Y', read_only=True)
    is_secondary_traveler = serializers.SerializerMethodField()
    primary_traveler_name = serializers.SerializerMethodField()

    class Meta:
        fields = ('reference_number', 'traveler', 'office', 'section', 'status', 'trip_type', 'partner', 'partnership',
                  'results', 'locations', 'start_date', 'end_date', 'is_secondary_traveler', 'primary_traveler_name')

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


class FinanceExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField()
    traveler = serializers.CharField(source='traveler.get_full_name', read_only=True)
    office = serializers.CharField(source='office.name', read_only=True)
    section = serializers.CharField(source='sector.name', read_only=True)
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
    section = serializers.CharField(source='travel.sector.name', read_only=True)
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
        data = super(TravelAdminExportSerializer, self).to_representation(instance)
        if 'dsa_area' not in data or not data['dsa_area']:
            data['dsa_area'] = 'NODSA'
        return data


class InvoiceExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='invoice.reference_number', read_only=True)
    ta_number = serializers.CharField(source='invoice.travel.reference_number', read_only=True)
    vendor_number = serializers.CharField(source='invoice.vendor_number', read_only=True)
    currency = serializers.CharField(source='invoice.currency.name', read_only=True)
    total_amount = serializers.DecimalField(source='invoice.amount', max_digits=20, decimal_places=4, read_only=True)
    status = serializers.CharField(source='invoice.status', read_only=True)
    message = serializers.CharField(source='invoice.message', read_only=True)
    vision_fi_doc = serializers.CharField(source='invoice.vision_fi_id', read_only=True)
    wbs = serializers.CharField(source='wbs.name', read_only=True)
    grant = serializers.CharField(source='grant.name', read_only=True)
    fund = serializers.CharField(source='fund.name', read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        fields = ('reference_number', 'ta_number', 'vendor_number', 'currency', 'total_amount', 'status', 'message',
                  'vision_fi_doc', 'wbs', 'grant', 'fund', 'amount')


class ActionPointExportSerializer(serializers.Serializer):
    action_point_number = serializers.CharField()
    trip_reference_number = serializers.CharField(source='travel.reference_number')
    description = serializers.CharField()
    due_date = serializers.DateTimeField()
    person_responsible = serializers.CharField(source='person_responsible.get_full_name')
    status = serializers.CharField()
    completed_date = serializers.DateTimeField(source='completed_at')
    actions_taken = serializers.CharField()
    flag_for_follow_up = serializers.BooleanField(source='follow_up')
    assigned_by = serializers.CharField(source='assigned_by.get_full_name')
    url = serializers.SerializerMethodField()

    class Meta:
        fields = ('action_point_number', 'trip_reference_number', 'description', 'due_date', 'person_responsible',
                  'status', 'completed_date', 'actions_taken', 'flag_for_follow_up', 'assigned_by', 'url')

    def get_url(self, obj):
        return None
