from __future__ import unicode_literals

from django.utils.translation import ugettext
from rest_framework import serializers

from t2f.models import Travel, ModeOfTravel
from t2f.serializers.travel import TravelListSerializer


class TravelListExportSerializer(TravelListSerializer):
    traveler = serializers.CharField(source='traveler.get_full_name')
    section = serializers.CharField(source='section.name')
    office = serializers.CharField(source='office.name')
    ta_reference_number = serializers.CharField(source='reference_number')
    approval_date = serializers.DateTimeField(source='approved_at')
    attachment_count = serializers.IntegerField(source='attachments.count')

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'start_date', 'end_date', 'status', 'created',
                  'section', 'office', 'supervisor', 'ta_required', 'ta_reference_number', 'approval_date', 'is_driver',
                  'attachment_count')


class FinanceExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField()
    traveler = serializers.CharField(source='traveler.get_full_name')
    office = serializers.CharField(source='office.name')
    section = serializers.CharField(source='section.name')
    status = serializers.CharField()
    supervisor = serializers.CharField(source='supervisor.get_full_name')
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    purpose_of_travel = serializers.CharField(source='purpose')
    mode_of_travel = serializers.SerializerMethodField()
    international_travel = serializers.BooleanField()
    require_ta = serializers.BooleanField(source='ta_required')
    dsa_total = serializers.DecimalField(source='cost_summary.dsa_total', max_digits=20, decimal_places=10)
    expense_total = serializers.DecimalField(source='cost_summary.expenses_total', max_digits=20, decimal_places=10)
    deductions_total = serializers.DecimalField(source='cost_summary.deductions_total', max_digits=20, decimal_places=10)

    class Meta:
        fields = ('reference_number', 'traveler', 'office', 'section', 'status', 'supervisor', 'start_date',
                  'end_date', 'purpose_of_travel', 'mode_of_travel', 'international_travel', 'require_ta', 'dsa_total',
                  'expense_total', 'deductions_total')

    def get_mode_of_travel(self, obj):
        return ', '.join(obj.mode_of_travel)


class YesOrEmptyField(serializers.BooleanField):
    def to_representation(self, value):
        value = super(YesOrEmptyField, self).to_representation(value)
        if value:
            return ugettext('Yes')
        return ''


class TravelAdminExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='travel.reference_number')
    traveler = serializers.CharField(source='travel.traveler.get_full_name')
    office = serializers.CharField(source='travel.office.name')
    section = serializers.CharField(source='travel.section.name')
    status = serializers.CharField(source='travel.status')
    origin = serializers.CharField()
    destination = serializers.CharField()
    departure_time = serializers.DateTimeField(source='departure_date', format='%d-%b-%Y %I:%M %p')
    arrival_time = serializers.DateTimeField(source='arrival_date', format='%d-%b-%Y %I:%M %p')
    dsa_area = serializers.CharField(source='dsa_region.area_code')
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
        if not data['dsa_area']:
            data['dsa_area'] = 'NODSA'
        return data


class InvoiceExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField(source='invoice.reference_number')
    ta_number = serializers.CharField(source='invoice.travel.reference_number')
    vendor_number = serializers.CharField(source='invoice.vendor_number')
    currency = serializers.CharField(source='invoice.currency.name')
    total_amount = serializers.DecimalField(source='invoice.amount', max_digits=20, decimal_places=4)
    status = serializers.CharField(source='invoice.status')
    message = serializers.CharField(source='invoice.message')
    vision_fi_doc = serializers.CharField(source='invoice.vision_fi_id')
    wbs = serializers.CharField(source='wbs.name')
    grant = serializers.CharField(source='grant.name')
    fund = serializers.CharField(source='fund.name')
    amount = serializers.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        fields = ('reference_number', 'ta_number', 'vendor_number', 'currency', 'total_amount', 'status', 'message',
                  'vision_fi_doc', 'wbs', 'grant', 'fund', 'amount')


class ActionPointExportSerializer(serializers.Serializer):
    action_point_number = serializers.CharField()
    trip_reference_number = serializers.CharField(source='travel.reference_number')
    description = serializers.CharField()
    due_date = serializers.DateTimeField()
    person_responsible = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.CharField()
    completed_date = serializers.DateTimeField(source='completed_at')
    actions_taken = serializers.CharField()
    flag_for_follow_up = serializers.BooleanField(source='follow_up')
    assigned_by = serializers.PrimaryKeyRelatedField(read_only=Travel)
    url = serializers.SerializerMethodField()

    class Meta:
        fields = ('action_point_number', 'trip_reference_number', 'description', 'due_date', 'person_responsible',
                  'status', 'completed_date', 'actions_taken', 'flag_for_follow_up', 'assigned_by', 'url')

    def get_url(self, obj):
        return None
