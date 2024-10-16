from rest_framework import serializers

from etools.applications.governments import models


class GovernmentEWPSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GovernmentEWP
        fields = '__all__'
