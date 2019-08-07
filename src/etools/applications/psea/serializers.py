from rest_framework import serializers

from etools.applications.psea.models import Engagement


class EngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Engagement
        fields = '__all__'
