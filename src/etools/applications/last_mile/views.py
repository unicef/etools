from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

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


class TransferViewSet(ModelViewSet):
    serializer_class = serializers.TransferSerializer
    queryset = models.Transfer.objects.select_related('shipment', 'partner_organization')

    # pagination_class = DynamicPageNumberPagination  # FE required
    permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request, *args, **kwargs):
        # destination_point == locationId
        qs = self.get_queryset().filter(status=models.Transfer.PENDING)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(destination_point_id=kwargs['locationId'])
        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(status=models.Transfer.CHECKED_IN)

        if 'locationId' in kwargs and kwargs['locationId']:
            qs = qs.filter(destination_point_id=kwargs['locationId']).exclude(origin_point_id=kwargs['locationId'])
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
