from functools import cache

from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
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
        .prefetch_related('partner_organizations')\
        .filter(is_active=True, private=True)
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('poi_type',)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    def get_queryset(self):
        partner_organization = getattr(self.request.user.profile.organization, 'partner', None)
        if partner_organization:
            return super().get_queryset().filter(partner_organizations=partner_organization)
        return models.PointOfInterest.objects.none()

    @action(detail=True, methods=['get'], url_path='items', serializer_class=serializers.ItemSerializer)
    def items(self, request, *args, pk=None, **kwargs):
        qs = models.Item.objects.filter(transfer__status=models.Transfer.COMPLETED, transfer__destination_point=pk)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)


class TransferViewSet(
    mixins.ListModelMixin,
    NestedViewSetMixin,
    GenericViewSet
):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects.select_related('partner_organization').prefetch_related('items')

    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    # TODO TBD
    search_fields = ('status', 'name', 'sequence_number')

    @cache
    def get_parent_object(self):
        return super().get_parent_object()

    def get_object(self):
        # validate against point_of_interest_pk
        return get_object_or_404(models.Transfer, pk=self.kwargs['pk'])

    def paginate_response(self, qs):
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        location = self.get_parent_object()
        qs = super().get_queryset()\
            .filter(destination_point=location, status=models.Transfer.PENDING)\
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
        qs = self.get_queryset()\
            .filter(status=models.Transfer.COMPLETED, origin_point=location)\
            .exclude(destination_point=location)

        return self.paginate_response(qs)

    @action(detail=True, methods=['patch'], url_path='new-check-in',
            serializer_class=serializers.TransferCheckinSerializer)
    def new_check_in(self, request, pk=None, **kwargs):
        transfer = get_object_or_404(models.Transfer, pk=pk)

        serializer = self.serializer_class(
            instance=transfer, data=request.data, partial=True,
            context={
                'request': request,
            })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None, **kwargs):
        transfer = get_object_or_404(models.Transfer, pk=pk)
        if transfer.transfer_type == models.Transfer.DISTRIBUTION:
            transfer.status = models.Transfer.COMPLETED
            transfer.save(update_fields=['status'])
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
