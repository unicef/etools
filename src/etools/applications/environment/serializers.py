
from rest_framework import serializers

from etools.applications.environment.models import TenantFlag, TenantSwitch


class TenantFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantFlag
        fields = ('name', 'countries', )


class TenantSwitchSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSwitch
        fields = ('name', 'countries', )
