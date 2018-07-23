
from rest_framework import serializers

from etools.applications.t2f.serializers import CostSummarySerializer


class CostAssignmentNameSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()

    class Meta:
        fields = ('name',)

    def get_name(self, obj):
        return '{} | {} | {}: {}%'.format(obj.wbs.name, obj.grant.name, obj.fund.name, obj.share)


class TravelMailSerializer(serializers.Serializer):
    estimated_travel_cost = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    supervisor = serializers.CharField(source='supervisor.get_full_name')
    traveler = serializers.CharField(source='traveler.get_full_name')
    start_date = serializers.DateTimeField(format='%m/%d/%Y')
    end_date = serializers.DateTimeField(format='%m/%d/%Y')
    currency = serializers.CharField(source='currency.code')
    cost_summary = CostSummarySerializer(read_only=True)
    location = serializers.CharField(source='itinerary.first.destination')
    cost_assignments = CostAssignmentNameSerializer(many=True)
    reference_number = serializers.CharField()
    purpose = serializers.CharField()
    rejection_note = serializers.CharField()

    class Meta:
        fields = ('traveler', 'supervisor', 'start_date', 'end_date', 'estimated_travel_cost', 'purpose',
                  'reference_number', 'currency', 'cost_summary', 'rejection_note', 'location', 'cost_assignments',
                  'reference_number', 'purpose', 'rejection_note')
