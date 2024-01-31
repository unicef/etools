from rest_framework import serializers

from etools.applications.last_mile.models import PointOfInterest


class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointOfInterest
        fields = '__all__'
