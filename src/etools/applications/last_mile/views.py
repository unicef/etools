from functools import cache

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
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.last_mile import models, serializers


class PointOfInterestTypeViewSet(ReadOnlyModelViewSet):
    queryset = models.PointOfInterestType.objects.all()
    serializer_class = serializers.PointOfInterestTypeSerializer


class PointOfInterestViewSet(ModelViewSet):
    serializer_class = serializers.PointOfInterestSerializer
    queryset = models.PointOfInterest.objects\
        .select_related('parent')\
        .prefetch_related('partner_organization')\
        .filter(is_active=True, private=True)  # TODO also filter by partner organization
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    @action(detail=True, methods=['get'], url_path='items', serializer_class=serializers.ItemSerializer)
    def items(self, request, *args, pk=None, **kwargs):
        qs = models.Item.objects.filter(location_id=pk)
        return Response(self.serializer_class(qs, many=True).data)


class TransferViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    NestedViewSetMixin,
    GenericViewSet
):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects.select_related('partner_organization')

    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    # TODO
    # search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    @cache
    def get_parent_object(self):
        return super().get_parent_object()

    def paginate_response(self, qs):
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = super().get_queryset().filter(status=models.Transfer.PENDING, items__status='transfer')

        qs_context = {'destination_point': location}

        if location.poi_type.name.lower() == 'warehouse':
            warehouse_context = {'destination_point__isnull': True}
            qs = qs.filter(Q(**qs_context) | Q(**warehouse_context))
        else:
            qs = qs.filter(qs_context)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = super().get_queryset().filter(
            destination_point=location,
            status=models.Transfer.CHECKED_IN
        )
        # shipment_context = {'origin_point__isnull': True,
        # }
        # transfer_context = {
        #     'status': models.Transfer.CHECKED_IN,
        # }
        # waybill_context = {
        #     'status': models.Transfer.WAYBILL
        # }
        qs = qs.filter(Q(origin_point__isnull=True) | ~Q(origin_point=location))

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='outgoing')
    def outgoing(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=models.Transfer.PENDING)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(origin_point=kwargs['locationId']).exclude(destination_point_id=kwargs['locationId'])
        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='completed')
    def completed(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=models.Transfer.COMPLETED)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(origin_point=kwargs['locationId']).exclude(destination_point_id=kwargs['locationId'])
        return self.paginate_response(qs)

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
