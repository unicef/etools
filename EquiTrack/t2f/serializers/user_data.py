from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from publics.models import BusinessArea
from t2f.helpers.misc import get_open_travels_for_check
from t2f.helpers.permission_matrix import get_user_role_list

log = logging.getLogger(__name__)


class T2FUserDataSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    travel_count = serializers.SerializerMethodField()
    business_area = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('roles', 'travel_count', 'business_area')

    def get_roles(self, obj):
        return get_user_role_list(obj)

    def get_travel_count(self, obj):
        return get_open_travels_for_check(obj).count()

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
