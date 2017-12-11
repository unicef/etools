from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from environment.models import TenantFlag, tenant_flag_is_active, TenantSwitch
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

        active_flags = [
            flag['name'] for flag in flag_serializer.data
            if tenant_flag_is_active(request, flag['name'])
        ]
        active_flags.extend([
            switch['name'] for switch in switch_serializer.data
            if switch.is_active()
        ])
        return Response({'active_flags': active_flags})
