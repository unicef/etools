from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from publics.models import BusinessArea
from t2f.models import UserTypes, Travel

log = logging.getLogger(__name__)


class T2FUserDataSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField('get_assigned_roles')
    travel_count = serializers.SerializerMethodField()
    business_area = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('roles', 'travel_count', 'business_area')

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

    def get_business_area(self, obj):
        workspace = obj.profile.country_override

        # If no override, use default
        if not workspace:
            workspace = obj.profile.country

            # If no default, cannot determine the business area
            if not workspace:
                return None

        if not workspace.business_area_code:
            return None

        try:
            return BusinessArea.objects.get(code=workspace.business_area_code).id
        except ObjectDoesNotExist:
            log.error('No model exists with business area code %s. Please investigate.', workspace.business_area_code)
            return None
