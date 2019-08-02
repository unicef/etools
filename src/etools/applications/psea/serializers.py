from rest_framework import serializers

from .models import PSEA


class PSEASerializer(serializers.ModelSerializer):
    class Meta:
        model = PSEA
        fields = '__all__'
