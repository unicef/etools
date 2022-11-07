from django.db import connection

from rest_framework import serializers

from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer


class InterventionSerializer(InterventionDetailSerializer):
    permissions = None
    available_actions = None
    business_area_code = serializers.SerializerMethodField()
    offices = serializers.SerializerMethodField()

    class Meta(InterventionDetailSerializer):
        fields = (
            f for f in InterventionDetailSerializer.Meta.fields
            if f not in {'permissions', 'available_actions'}
        )

    def get_user(self):
        """
        evidently disallow current user usage to avoid data inconsistencies
        """
        raise NotImplementedError

    def get_business_area_code(self, _obj):
        return connection.tenant.business_area_code

    def get_offices(self, obj):
        return list(obj.offices.values_list('offices', flat=True))
