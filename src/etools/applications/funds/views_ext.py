from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction

from rest_framework import status
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_restlib.views import SafeTenantViewSetMixin

from etools.applications.core.auth import eToolsEZHactTokenAuth
from etools.applications.funds.serializers import (
    GPDExternalFundsReservationSerializer,
    PDExternalFundsReservationSerializer,
)
from etools.applications.governments.models import GDD
from etools.applications.governments.views.gdd import GDDAutoTransitionsMixin
from etools.applications.partners.models import Intervention
from etools.applications.partners.views.interventions_v3 import InterventionAutoTransitionsMixin
from etools.applications.vision.models import VisionSyncLog


class PDExternalReservationAPIView(SafeTenantViewSetMixin, CreateAPIView, InterventionAutoTransitionsMixin):
    """
    External endpoint that creates FundsReservation header and items for a given pd reference number
    """
    authentication_classes = [eToolsEZHactTokenAuth]
    permission_classes = [IsAuthenticated]
    serializer_class = PDExternalFundsReservationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        log = VisionSyncLog(
            country=connection.tenant,
            business_area_code=connection.tenant.business_area_code,
            handler_name='EZHactPDFundsReservation',
            data=request.data,
            total_processed=1, total_records=1
        )
        try:
            with transaction.atomic():
                serializer.is_valid(raise_exception=True)
                intervention = get_object_or_404(Intervention, number=serializer.validated_data.get('pd_reference_number'))
                serializer.save(intervention=intervention)

                admin_user = get_object_or_404(get_user_model(), username=settings.TASK_ADMIN_USER)
                self.perform_auto_transitions(intervention=intervention, user=admin_user)
        except Exception as e:
            log.exception_message = e.__str__()
            raise e
        else:
            log.successful = True
        finally:
            log.save()

        return Response(status=status.HTTP_201_CREATED)


class GPDExternalReservationAPIView(SafeTenantViewSetMixin, CreateAPIView, GDDAutoTransitionsMixin):
    """
    External endpoint that creates FundsReservation header and items for a given gpd reference number
    """
    authentication_classes = [eToolsEZHactTokenAuth]
    permission_classes = [IsAuthenticated]
    serializer_class = GPDExternalFundsReservationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        log = VisionSyncLog(
            country=connection.tenant,
            business_area_code=connection.tenant.business_area_code,
            handler_name='EZHactGPDFundsReservation',
            data=request.data,
            total_processed=1, total_records=1
        )
        try:
            with transaction.atomic():
                serializer.is_valid(raise_exception=True)
                gdd = get_object_or_404(GDD, number=serializer.validated_data.get('gpd_reference_number'))
                serializer.save(gdd=gdd)

                admin_user = get_object_or_404(get_user_model(), username=settings.TASK_ADMIN_USER)
                self.perform_auto_transitions(gdd=gdd, user=admin_user)
        except Exception as e:
            log.exception_message = e.__str__()
            raise e
        else:
            log.successful = True
        finally:
            log.save()

        return Response(status=status.HTTP_201_CREATED)
