from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from environment.helpers import tenant_flag_is_active, tenant_switch_is_active
from environment.models import TenantFlag, TenantSwitch
from environment.serializers import TenantFlagSerializer, TenantSwitchSerializer

# API Views


class ActiveFlagAPIView(ListAPIView):
    """
    Read-only API to get a list of all active flags or switches for this request under the key
    `active_flags`
    """

    def list(self, request, *args, **kwargs):
        """
        Override list() to check each flag against this request and return just a
        list of active flags.
        """
        flag_serializer = TenantFlagSerializer(TenantFlag.objects, many=True)
        switch_serializer = TenantSwitchSerializer(TenantSwitch.objects, many=True)

        # use set comprehensions so we never get dupes in this list
        active_flags = {
            flag['name'] for flag in flag_serializer.data
            if tenant_flag_is_active(request, flag['name'])
        }
        active_flags.update([
            switch['name'] for switch in switch_serializer.data
            if tenant_switch_is_active(switch['name'])
        ])
        return Response({'active_flags': list(active_flags)})
