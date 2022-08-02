from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.ecn.serializers import ECNSyncSerializer
from etools.applications.ecn.synchronizer import ECNSynchronizer
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, user_group_permission
from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer


class ECNSyncView(GenericAPIView):
    permission_classes = [IsAuthenticated, user_group_permission(PARTNERSHIP_MANAGER_GROUP)]

    def post(self, request, *args, **kwargs):
        serializer = ECNSyncSerializer(context=self.get_serializer_context(), data=request.data)
        serializer.is_valid(raise_exception=True)
        synchronizer = ECNSynchronizer(request.user)
        intervention = synchronizer.synchronize(
            serializer.validated_data['number'],
            serializer.validated_data['agreement'],
        )
        if not intervention:
            return Response(status=404)

        return Response(
            InterventionDetailSerializer(intervention, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )
