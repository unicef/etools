from __future__ import unicode_literals

from rest_framework import serializers

from t2f.models import Travel
from t2f.serializers import TravelListSerializer


class TravelListExportSerializer(TravelListSerializer):
    traveler = serializers.CharField(source='traveler.get_full_name')
    section = serializers.CharField(source='section.name')
    office = serializers.CharField(source='office.name')

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'status', 'section', 'office', 'start_date',
                  'end_date')
