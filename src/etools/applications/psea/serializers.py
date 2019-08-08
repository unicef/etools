from rest_framework import serializers

from etools.applications.psea.models import Assessment


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = '__all__'
