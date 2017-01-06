from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers

from t2f.models import UserTypes, Travel


class T2FUserDataSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField('get_assigned_roles')
    travel_count = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('roles', 'travel_count')

    def get_assigned_roles(self, obj):
        roles = [UserTypes.ANYONE]

        if obj.groups.filter(name='Representative Office').exists():
            roles.append(UserTypes.REPRESENTATIVE)

        if obj.groups.filter(name='Finance Focal Point').exists():
            roles.append(UserTypes.FINANCE_FOCAL_POINT)

        if obj.groups.filter(name='Travel Focal Point').exists():
            roles.append(UserTypes.TRAVEL_FOCAL_POINT)

        if obj.groups.filter(name='Travel Administrator').exists():
            roles.append(UserTypes.TRAVEL_ADMINISTRATOR)

        return roles

    def get_travel_count(self, obj):
        excluded_statuses = [Travel.CANCELLED,
                             Travel.CERTIFIED,
                             Travel.COMPLETED]
        return Travel.objects.filter(traveler=obj).exclude(status__in=excluded_statuses).count()
