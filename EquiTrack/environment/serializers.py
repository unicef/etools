from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import serializers

from environment.models import TenantFlag, TenantSwitch


class TenantFlagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='flag.name')

    class Meta:
        model = TenantFlag
        fields = ('name', 'countries', )


class TenantSwitchSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSwitch
        fields = ('name', 'countries', )
