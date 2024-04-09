from functools import cache

from django.db import connection
from django.db.models import CharField, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.last_mile import models, serializers
from etools.applications.last_mile.permissions import IsIPLMEditor
from etools.applications.last_mile.tasks import notify_upload_waybill


class PointOfInterestTypeViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsIPLMEditor]
    queryset = models.PointOfInterestType.objects.all()
    serializer_class = serializers.PointOfInterestTypeSerializer


class POIQuerysetMixin:
    def get_poi_queryset(self):
        partner = self.request.user.partner
        if partner:
            return (models.PointOfInterest.objects
                    .filter(Q(partner_organizations=partner) | Q(partner_organizations__isnull=True))
                    .filter(is_active=True)
                    .select_related('parent')
                    .prefetch_related('partner_organizations')
                    .order_by('name', 'id'))
        return models.PointOfInterest.objects.none()


class PointOfInterestViewSet(POIQuerysetMixin, ModelViewSet):
    serializer_class = serializers.PointOfInterestSerializer
    permission_classes = [IsIPLMEditor]
    pagination_class = DynamicPageNumberPagination

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('poi_type',)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    def get_queryset(self):
        return self.get_poi_queryset()

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
    permission_classes = [IsIPLMEditor]
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
                .exclude(transfer__transfer_type=models.Transfer.WASTAGE)\
                .order_by('created', '-id')
            return qs
        return self.queryset.none()


class InventoryMaterialsListView(POIQuerysetMixin, ListAPIView):
    permission_classes = [IsIPLMEditor]
    serializer_class = serializers.MaterialListSerializer
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = (
        'items__uom', 'items__batch_id', 'items__shipment_item_id',
        'short_description', 'basic_description', 'hazardous_goods', 'hazardous_goods_description',
        'group', 'group_description', 'original_uom', 'material_type', 'material_type_description',
        'purchase_group', 'purchase_group_description', 'temperature_group', 'temperature_conditions'
    )

    def get_queryset(self):
        if self.request.parser_context['kwargs'] and 'poi_pk' in self.request.parser_context['kwargs']:
            poi = get_object_or_404(self.get_poi_queryset(), pk=self.request.parser_context['kwargs']['poi_pk'])
            partner = self.request.user.partner
            if not partner:
                return self.queryset.none()
            items_qs = models.Item.objects\
                .select_related('transfer', 'transfer__partner_organization', 'transfer__destination_point')\
                .filter(transfer__status=models.Transfer.COMPLETED,
                        transfer__destination_point=poi.pk,
                        transfer__partner_organization=partner)\
                .exclude(transfer__transfer_type=models.Transfer.WASTAGE)\

            qs = models.Material.objects\
                .filter(items__in=items_qs)\
                .prefetch_related(Prefetch('items', queryset=items_qs))\
                .distinct()\
                .order_by('id', 'short_description')

            return qs
        return self.queryset.none()


class TransferViewSet(
    POIQuerysetMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects.all().order_by('created', '-id')

    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsIPLMEditor]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'partner_organization__organization__name',
                     'comment', 'pd_number', 'unicef_release_order', 'waybill_id')

    def get_queryset(self):
        partner = self.request.user.partner
        if not partner:
            return models.Transfer.objects.none()
        qs = super(TransferViewSet, self).get_queryset()\
            .select_related('partner_organization',
                            'destination_point', 'origin_point',
                            'checked_in_by', 'checked_out_by', 'origin_transfer')\
            .filter(partner_organization=partner)
        return qs

    def detail_qs(self):
        return self.get_queryset().prefetch_related(
            Prefetch(
                'items', models.Item.objects
                .select_related('material')
                .prefetch_related('transfers_history')
                .annotate(description=Subquery(models.PartnerMaterial.objects.filter(
                    partner_organization=self.request.user.partner,
                    material=OuterRef('material')).values('description'), output_field=CharField())))
        )

    @cache
    def get_parent_poi(self):
        return get_object_or_404(self.get_poi_queryset(), pk=self.kwargs['point_of_interest_pk'])

    def get_object(self):
        return get_object_or_404(self.detail_qs(), pk=self.kwargs['pk'])

    def paginate_response(self, qs):
        page = self.paginate_queryset(self.filter_queryset(qs))
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        location = self.get_parent_poi()

        self.serializer_class = serializers.TransferListSerializer
        qs = super(TransferViewSet, self).get_queryset()
        qs = (qs.filter(status=models.Transfer.PENDING)
              .filter(Q(destination_point=location) | Q(destination_point__isnull=True))
              .exclude(origin_point=location).select_related("destination_point__parent", "origin_point__parent"))

        return self.paginate_response(qs)

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, *args, **kwargs):
        transfer = self.get_object()
        return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        location = self.get_parent_poi()
        qs = super().get_queryset()\
            .filter(status=models.Transfer.COMPLETED, destination_point=location)\
            .exclude(origin_point=location)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='outgoing')
    def outgoing(self, request, *args, **kwargs):
        location = self.get_parent_poi()
        qs = self.get_queryset()\
            .filter(status=models.Transfer.PENDING, origin_point=location)\
            .exclude(destination_point=location)

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='completed')
    def completed(self, request, *args, **kwargs):
        location = self.get_parent_poi()

        completed_filters = Q()
        completed_filters |= Q(Q(origin_point=location) & ~Q(destination_point=location))
        completed_filters |= Q(destination_point=location, transfer_type=models.Transfer.WASTAGE)

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
                'location': self.get_parent_poi()
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
                'location': self.get_parent_poi()
            })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializers.TransferSerializer(serializer.instance).data, status=status.HTTP_200_OK)


class ItemUpdateViewSet(mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    queryset = models.Item.objects.all()
    serializer_class = serializers.ItemUpdateSerializer
