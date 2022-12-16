from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.ecn.serializers import ECNSyncSerializer
from etools.applications.ecn.synchronizer import ECNSynchronizer, InterventionNotReadyException
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, user_group_permission
from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer


class ECNSyncView(GenericAPIView):
    permission_classes = [IsAuthenticated, user_group_permission(PARTNERSHIP_MANAGER_GROUP)]

    def post(self, request, *args, **kwargs):
        serializer = ECNSyncSerializer(context=self.get_serializer_context(), data=request.data)
        serializer.is_valid(raise_exception=True)
        synchronizer = ECNSynchronizer(request.user)
        try:
            intervention = synchronizer.synchronize(**serializer.validated_data)
        except InterventionNotReadyException:
            return Response(
                {'non_field_errors': [_('Intervention is not ready for import yet')]},
                status=status.HTTP_400_BAD_REQUEST,
                headers=self.headers,
            )

        if not intervention:
            return Response(status=404)

        return Response(
            InterventionDetailSerializer(intervention, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )
