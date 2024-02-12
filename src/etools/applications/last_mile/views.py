from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

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

    @action(detail=True, methods=['get'], url_path='items', serializer_class=serializers.ItemSerializer)
    def items(self, request, *args, pk=None, **kwargs):
        print(pk)
        qs = models.Item.objects.filter(location_id=pk)
        return Response(self.serializer_class(qs, many=True).data)


class ShipmentUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    """
    Updates only the waybill #
    """
    queryset = models.Shipment.objects.all()
    serializer_class = serializers.ShipmentSerializer
    permission_classes = [IsAuthenticated]


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

    @action(detail=True, methods=['patch'], url_path='upload-proof',
            parser_classes=(FormParser, MultiPartParser,))
    def upload_proof(self, request, pk=None):
        transfer = get_object_or_404(models.Transfer, pk=pk)
        proof_file = request.data.get('file')
        transfer.proof_file.save(proof_file.name, proof_file)
        return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='check-in',
            serializer_class=serializers.TransferCheckinSerializer)
    def check_in(self, request, pk=None):
        transfer = get_object_or_404(models.Transfer, pk=pk)

        serializer = serializers.TransferCheckinSerializer(instance=transfer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        transfer.status = models.Transfer.CHECKED_IN
        transfer.checked_in_by = request.user
        transfer.save(update_fields=['status', 'checked_in_by'])

        transfer.items.update(location_id=serializer.validated_data['locationId'])

        return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_200_OK)
