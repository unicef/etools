from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from etools.applications.last_mile import models, serializers


class PointOfInterestViewSet(ModelViewSet):
    serializer_class = serializers.PointOfInterestSerializer
    queryset = models.PointOfInterest.objects\
        .select_related('parent')\
        .prefetch_related('partner_organization')\
        .filter(is_active=True, private=True)  # TODO also filter by partner organization
    # pagination_class = DynamicPageNumberPagination  # FE required
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')


class TransferViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects.select_related('shipment', 'partner_organization')

    # pagination_class = DynamicPageNumberPagination  # FE required
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        # TODO change to RESTFUL endpoints: /location/<loc-id>/incoming-transfers/
        #  instead of 'mandatory' locationId query param
        if 'locationId' not in request.query_params or not request.query_params['locationId']:
            raise ValidationError(_('The location Id must be provided.'))

        location = get_object_or_404(models.PointOfInterest.objects, pk=request.query_params['locationId'])
        qs = super().get_queryset().filter(status=models.Transfer.PENDING)

        qs_context = {
            'shipment__isnull': True,
            'destination_point': location,
            'items__status': 'transfer'
        }
        if location.poi_type.name.lower() == 'warehouse':
            warehouse_context = {
                'shipment__isnull': False,
                'destination_point__isnull': True,
                'items__status': 'shipment'
            }
            qs = qs.filter(Q(**qs_context) | Q(**warehouse_context))
        else:
            qs = qs.filter(qs_context)

        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        if 'locationId' not in request.query_params or not request.query_params['locationId']:
            raise ValidationError(_('The location Id must be provided.'))

        location = get_object_or_404(models.PointOfInterest.objects, pk=request.query_params['locationId'])
        qs = super().get_queryset().filter(destination_point=location)
        shipment_context = {
            'status': models.Transfer.CHECKED_IN,
            'shipment__isnull': False,
            'origin_point__isnull': True,
            # TODO TBD: OR [{reason: {not: TransferStatus.Distribution}}, {reason: {equals: null}} ]
        }
        transfer_context = {
            'status': models.Transfer.CHECKED_IN,
            'shipment__isnull': True,
        }
        waybill_context = {
            'status': models.Transfer.WAYBILL
        }
        qs = qs.filter(
            Q(**shipment_context) |
            (Q(**transfer_context) | ~Q(origin_point=location)) |
            Q(**waybill_context))
        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='outgoing')
    def outgoing(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=models.Transfer.PENDING)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(origin_point=kwargs['locationId']).exclude(destination_point_id=kwargs['locationId'])
        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='completed')
    def completed(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=models.Transfer.CHECKED_IN)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(origin_point=kwargs['locationId']).exclude(destination_point_id=kwargs['locationId'])
        return Response(self.serializer_class(qs, many=True).data)
