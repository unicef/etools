from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import status
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_restlib.views import SafeTenantViewSetMixin

from etools.applications.core.auth import eToolsEZHactTokenAuth
from etools.applications.funds.serializers import ExternalFundsReservationSerializer
from etools.applications.partners.models import Intervention
from etools.applications.partners.views.interventions_v3 import InterventionAutoTransitionsMixin


class ExternalReservationAPIView(SafeTenantViewSetMixin, CreateAPIView, InterventionAutoTransitionsMixin):
    """
    External endpoint that creates FundsReservation header and items for a given pd reference number
    """
    authentication_classes = [eToolsEZHactTokenAuth]
    permission_classes = [IsAuthenticated]
    serializer_class = ExternalFundsReservationSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        intervention = get_object_or_404(Intervention, number=serializer.validated_data.get('pd_reference_number'))
        serializer.save(intervention=intervention)

        admin_user = get_object_or_404(get_user_model(), username=settings.TASK_ADMIN_USER)
        self.perform_auto_transitions(intervention=intervention, user=admin_user)

        return Response(status=status.HTTP_201_CREATED)
