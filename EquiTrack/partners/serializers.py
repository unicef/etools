__author__ = 'jcranwellward'

import json

from rest_framework import serializers

from .models import GwPCALocation


class GWLocationSerializer(serializers.ModelSerializer):

    pca_title = serializers.CharField(source='pca.title')
    pca_number = serializers.CharField(source='pca.number')
    pca_id = serializers.CharField(source='pca.id')
    partner_name = serializers.CharField(source='pca.partner.name')
    partner_id = serializers.CharField(source='pca.partner.id')
    sector_name = serializers.CharField(source='pca.sectors')
    sector_id = serializers.CharField(source='pca.sector_id')
    latitude = serializers.CharField(source='location.point.y')
    longitude = serializers.CharField(source='location.point.x')
    location_name = serializers.CharField(source='location.name')
    location_type = serializers.CharField(source='location.gateway.name')
    gateway_name = serializers.CharField(source='location.gateway.name')
    gateway_id = serializers.CharField(source='location.gateway.id')

    class Meta:
        model = GwPCALocation


class RapidProRequest(serializers.Serializer):

    relayer	= serializers.CharField()
    phone = serializers.CharField(required=True)
    text = serializers.CharField(required=True)
    flow = serializers.CharField()
    step = serializers.CharField()
    time = serializers.DateTimeField()
    values = serializers.CharField()

    def restore_fields(self, data, files):

        restored_data = super(RapidProRequest, self).restore_fields(data, files)
        if restored_data['values']:
            restored_data['values'] = json.loads(restored_data['values'])
        return restored_data
