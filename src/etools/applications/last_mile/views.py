from functools import cache

from django.db import connection
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.last_mile import models, serializers
from etools.applications.last_mile.tasks import notify_upload_waybill


class PointOfInterestTypeViewSet(ReadOnlyModelViewSet):
    queryset = models.PointOfInterestType.objects.all()
    serializer_class = serializers.PointOfInterestTypeSerializer


class PointOfInterestViewSet(ModelViewSet):
    serializer_class = serializers.PointOfInterestSerializer
    queryset = models.PointOfInterest.objects\
        .select_related('parent')\
        .prefetch_related('partner_organizations')\
        .filter(is_active=True, private=True)\
        .order_by('name')
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('poi_type',)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    def get_queryset(self):
        partner_organization = getattr(self.request.user.profile.organization, 'partner', None)
        if partner_organization:
            return super().get_queryset().filter(partner_organizations=partner_organization)
        return models.PointOfInterest.objects.none()

    @action(detail=True, methods=['post'], url_path='upload-waybill',
            serializer_class=serializers.WaybillTransferSerializer)
    def upload_waybill(self, request, pk=None):
        destination_point = get_object_or_404(models.PointOfInterest, pk=pk)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        waybill_file = serializer.validated_data['waybill_file']
        waybill_url = request.build_absolute_uri(waybill_file.url)
        notify_upload_waybill.delay(
            connection.schema_name, destination_point.pk, waybill_file.pk, waybill_url
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryItemListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ItemListSerializer
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = (
        'description', 'uom', 'batch_id', 'transfer__name', 'shipment_item_id',
        'material__short_description', 'material__basic_description',
        'material__group_description', 'material__original_uom',
        'material__purchase_group', 'material__purchase_group_description', 'material__temperature_group'
    )

    def get_queryset(self):
        if self.request.parser_context['kwargs'] and 'poi_pk' in self.request.parser_context['kwargs']:
            poi = get_object_or_404(models.PointOfInterest, pk=self.request.parser_context['kwargs']['poi_pk'])
            qs = models.Item.objects\
                .filter(transfer__status=models.Transfer.COMPLETED, transfer__destination_point=poi.pk)\
                .exclude(transfer__transfer_type=models.Transfer.LOSS)\
                .order_by('id')
            return qs
        return self.queryset.none()


class InventoryMaterialsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.MaterialListSerializer
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = (
        'description', 'uom', 'batch_id', 'transfer__name', 'shipment_item_id',
        'material__short_description', 'material__basic_description',
        'material__group_description', 'material__original_uom',
        'material__purchase_group', 'material__purchase_group_description', 'material__temperature_group'
    )

    def get_queryset(self):
        if self.request.parser_context['kwargs'] and 'poi_pk' in self.request.parser_context['kwargs']:
            poi = get_object_or_404(models.PointOfInterest, pk=self.request.parser_context['kwargs']['poi_pk'])

            items_qs = models.Item.objects\
                .filter(transfer__status=models.Transfer.COMPLETED, transfer__destination_point=poi.pk)\
                .exclude(transfer__transfer_type=models.Transfer.LOSS)\

            qs = models.Material.objects\
                .filter(items__in=items_qs)\
                .prefetch_related(Prefetch('items', queryset=items_qs))

            return qs
        return self.queryset.none()


class TransferViewSet(
    mixins.ListModelMixin,
    GenericViewSet
):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects\
        .select_related('partner_organization')\
        .prefetch_related('items')\
        .order_by('created')

    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'partner_organization__organization__name', 'comment', 'e_tools_reference')

    @cache
    def get_parent_object(self):
        return get_object_or_404(models.PointOfInterest, pk=self.kwargs['point_of_interest_pk'])

    def get_object(self):
        return get_object_or_404(models.Transfer, pk=self.kwargs['pk'])

    def paginate_response(self, qs):
        page = self.paginate_queryset(self.filter_queryset(qs))
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = super().get_queryset()\
            .filter(status=models.Transfer.PENDING, destination_point=location)\
            .exclude(origin_point=location)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = super().get_queryset()\
            .filter(status=models.Transfer.COMPLETED, destination_point=location)\
            .exclude(origin_point=location)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='outgoing')
    def outgoing(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = self.get_queryset()\
            .filter(status=models.Transfer.PENDING, origin_point=location)\
            .exclude(destination_point=location)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='completed')
    def completed(self, request, *args, **kwargs):
        location = self.get_parent_object()

        completed_filters = Q()
        completed_filters |= Q(Q(origin_point=location) & ~Q(destination_point=location))
        completed_filters |= Q(destination_point=location, transfer_type=models.Transfer.LOSS)

        qs = self.get_queryset().filter(status=models.Transfer.COMPLETED).filter(completed_filters)
        return self.paginate_response(qs)

    @action(detail=True, methods=['patch'], url_path='new-check-in',
            serializer_class=serializers.TransferCheckinSerializer)
    def new_check_in(self, request, pk=None, **kwargs):
        transfer = self.get_object()

        serializer = self.serializer_class(
            instance=transfer, data=request.data, partial=True,
            context={
                'request': request,
                'location': self.get_parent_object()
            })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializers.TransferSerializer(serializer.instance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None, **kwargs):
        transfer = self.get_object()
        if transfer.transfer_type == models.Transfer.DISTRIBUTION:
            transfer.status = models.Transfer.COMPLETED

        transfer.destination_check_in_at = timezone.now()
        transfer.checked_in_by = request.user
        transfer.save(update_fields=['status', 'destination_check_in_at', 'checked_in_by'])
        return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='new-check-out',
            serializer_class=serializers.TransferCheckOutSerializer)
    def new_check_out(self, request, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={
                'request': request,
                'location': self.get_parent_object()
            })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializers.TransferSerializer(serializer.instance).data, status=status.HTTP_200_OK)


class ItemUpdateViewSet(mixins.UpdateModelMixin, GenericViewSet):
    queryset = models.Item.objects.all()
    serializer_class = serializers.ItemUpdateSerializer
