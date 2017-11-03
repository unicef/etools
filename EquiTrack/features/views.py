from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from features.models import TenantFlag, tenant_flag_is_active
from features.serializers import TenantFlagSerializer


class ActiveFlagAPIView(ListAPIView):
    """
    Read-only API to get a list of active flags for this request under the key
    `active_flags`
    """
    serializer_class = TenantFlagSerializer
    queryset = TenantFlag.objects

    def list(self, request, *args, **kwargs):
        """
        Override list() to check each flag against this request and return just a
        list of active flags.
        """
        serializer = self.get_serializer(self.get_queryset(), many=True)
        active_flags = [
            flag['name'] for flag in serializer.data
            if tenant_flag_is_active(request, flag['name'])
        ]
        return Response({'active_flags': active_flags})
