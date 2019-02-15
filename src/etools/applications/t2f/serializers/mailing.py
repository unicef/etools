from rest_framework import serializers


class TravelMailSerializer(serializers.Serializer):
    estimated_travel_cost = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    supervisor = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    traveler = serializers.CharField(source='traveler.get_full_name', read_only=True)
    start_date = serializers.DateTimeField(format='%m/%d/%Y')
    end_date = serializers.DateTimeField(format='%m/%d/%Y')
    currency = serializers.CharField(source='currency.code', read_only=True)
    location = serializers.CharField(source='itinerary.first.destination', read_only=True)
    reference_number = serializers.CharField()
    purpose = serializers.CharField()
    rejection_note = serializers.CharField()

    class Meta:
        fields = ('traveler', 'supervisor', 'start_date', 'end_date', 'estimated_travel_cost', 'purpose',
                  'reference_number', 'currency', 'rejection_note', 'location', 'rejection_note')
