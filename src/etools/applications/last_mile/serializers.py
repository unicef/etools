from django.db import connection

from rest_framework import serializers

from etools.applications.last_mile import models


class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['country'] = connection.tenant.name
        data['region'] = instance.parent.name
        data['typePrimary'] = instance.poi_type.name
        data['typeSecondary'] = instance.description
        data['lat'] = instance.point.y
        data['long'] = instance.point.x
        return data


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Transfer
        fields = '__all__'

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
        # data['country'] = connection.tenant.name
        # data['region'] = instance.parent.name
        # data['typePrimary'] = instance.poi_type.name
        # data['typeSecondary'] = instance.description
        # data['lat'] = instance.point.y
        # data['long'] = instance.point.x
        # return data
