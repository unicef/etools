from functools import cache

from django.conf import settings
from django.db import connection
from django.db.models import F, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.last_mile import models, serializers
from etools.applications.last_mile.filters import POIFilter, TransferFilter
from etools.applications.last_mile.permissions import IsIPLMEditor
from etools.applications.last_mile.tasks import notify_upload_waybill
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.utils.pbi_auth import get_access_token, get_embed_token, get_embed_url, TokenRetrieveException


class PointOfInterestTypeViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsIPLMEditor]
    queryset = models.PointOfInterestType.objects.all()
    serializer_class = serializers.PointOfInterestTypeSerializer


class POIQuerysetMixin:
    def get_poi_queryset(self, exclude_partner_prefetch=False):
        partner = self.request.user.partner
        if partner:
            user_has_assigned_poi = models.UserPointsOfInterest.objects.filter(
                user=self.request.user
            ).exists()

            base_qs = models.PointOfInterest.objects \
                .filter(is_active=True) \
                .exclude(name="UNICEF Warehouse") \
                .select_related('parent', 'poi_type').defer('parent__point', 'parent__geom', 'point') \
                .order_by('name', 'id')

            if user_has_assigned_poi:
                qs = base_qs.filter(users__user__id=self.request.user.id)
            else:
                qs = base_qs.filter(Q(partner_organizations=partner) | Q(partner_organizations__isnull=True))

            if not exclude_partner_prefetch:
                qs = qs.prefetch_related('partner_organizations')
            return qs
        return models.PointOfInterest.objects.none()


class PointOfInterestViewSet(POIQuerysetMixin, ModelViewSet):
    serializer_class = serializers.PointOfInterestSerializer
    permission_classes = [IsIPLMEditor]
    pagination_class = DynamicPageNumberPagination

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = POIFilter
    search_fields = ('name', 'p_code', 'parent__name', 'parent__p_code')

    def get_queryset(self):
        return self.get_poi_queryset(exclude_partner_prefetch=True).only(
            'parent__name', 'p_code', 'name', 'is_active', 'description', 'poi_type', 'secondary_type', 'status', 'created_on', 'approved_on', 'review_notes', 'created_by_id', 'approved_by_id'
        )

    @action(detail=True, methods=['post'], url_path='upload-waybill',
            serializer_class=serializers.WaybillTransferSerializer)
    def upload_waybill(self, request, pk=None):
        destination_point = get_object_or_404(models.PointOfInterest, pk=pk)

        serializer = self.serializer_class(data=request.data, context={'partner': request.user.partner})
        serializer.is_valid(raise_exception=True)
        waybill_file = serializer.validated_data['waybill_file']
        waybill_url = request.build_absolute_uri(waybill_file.url)
        notify_upload_waybill.delay(
            connection.schema_name, destination_point.pk, waybill_file.pk, waybill_url
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class HandoverPartnerListViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = MinimalPartnerOrganizationListSerializer
    permission_classes = [IsIPLMEditor]
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    def get_queryset(self):
        return PartnerOrganization.objects.filter(hidden=False, deleted_flag=False, organization__name__gt='').values('id', 'name')


class InventoryItemListView(POIQuerysetMixin, ListAPIView):
    permission_classes = [IsIPLMEditor]
    serializer_class = serializers.ItemSimpleListSerializer
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = (
        'description', 'batch_id', 'transfer__name',
        'material__short_description', 'material__group_description',
        'material__purchase_group', 'material__purchase_group_description', 'material__temperature_group', 'mapped_description'
    )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['country'] = connection.tenant.name
        return context

    def get_queryset(self):
        if self.request.parser_context['kwargs'] and 'poi_pk' in self.request.parser_context['kwargs']:
            poi = get_object_or_404(self.get_poi_queryset(), pk=self.request.parser_context['kwargs']['poi_pk'])
            partner = self.request.user.partner
            if not partner:
                return self.queryset.none()

            qs = models.Item.objects\
                .filter(transfer__partner_organization=partner,
                        transfer__status=models.Transfer.COMPLETED,
                        transfer__destination_point=poi.pk)\
                .exclude(transfer__transfer_type__in=[models.Transfer.WASTAGE, models.Transfer.DISPENSE])

            qs = qs.select_related('transfer',
                                   'material',
                                   'transfer__partner_organization',
                                   'transfer__destination_point',
                                   'transfer__origin_point',
                                   'transfer__checked_in_by',
                                   'transfer__checked_out_by')

            qs = qs.annotate(description=F('material__short_description'))
            return qs
        return self.queryset.none()


class InventoryMaterialsViewSet(POIQuerysetMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = serializers.MaterialListSerializer
    pagination_class = DynamicPageNumberPagination

    filter_backends = (SearchFilter,)
    search_fields = (
        'items__batch_id', 'number',
        'short_description', 'hazardous_goods', 'hazardous_goods_description',
        'group', 'group_description', 'material_type', 'material_type_description',
        'purchase_group', 'purchase_group_description', 'temperature_group', 'temperature_conditions'
    )

    def get_queryset(self):
        poi = get_object_or_404(self.get_poi_queryset(), pk=self.kwargs['point_of_interest_pk'])
        partner = self.request.user.partner
        if not partner:
            return self.queryset.none()
        items_qs = models.Item.objects\
            .select_related('transfer',
                            'transfer__partner_organization',
                            'transfer__partner_organization__organization',
                            'transfer__origin_point',
                            'transfer__origin_point__parent',
                            'transfer__checked_in_by',
                            'transfer__destination_point__parent',
                            'transfer__destination_point')\
            .filter(transfer__status=models.Transfer.COMPLETED,
                    transfer__destination_point=poi.pk,
                    transfer__partner_organization=partner)\
            .exclude(transfer__transfer_type__in=[models.Transfer.WASTAGE, models.Transfer.DISPENSE])\
            .defer('transfer__origin_point__point',
                   'transfer__destination_point__point',
                   'transfer__origin_point__parent__geom',
                   'transfer__origin_point__parent__point',
                   'transfer__origin_point__parent__parent',
                   'transfer__destination_point__parent__geom',
                   'transfer__destination_point__parent__point',
                   'transfer__destination_point__parent__parent')

        qs = models.Material.objects\
            .filter(items__in=items_qs)\
            .prefetch_related(Prefetch('items', queryset=items_qs)) \
            .annotate(description=F('short_description'))\
            .distinct()\
            .order_by('id', 'short_description')

        return qs

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, *args, **kwargs):
        material = self.get_object()
        return Response(serializers.MaterialDetailSerializer(material).data, status=status.HTTP_200_OK)


class TransferViewSet(
    POIQuerysetMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    serializer_class = serializers.TransferListSerializer
    queryset = models.Transfer.objects.all().order_by('created', '-id')

    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsIPLMEditor]

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = TransferFilter
    search_fields = ('name', 'partner_organization__organization__name',
                     'comment', 'pd_number', 'unicef_release_order', 'waybill_id')

    def get_queryset(self, handover=False):
        partner = self.request.user.partner
        if not partner:
            return models.Transfer.objects.none()
        qs = (super(TransferViewSet, self).get_queryset()
              .select_related('destination_point', 'origin_point',
                              'destination_point__parent', 'origin_point__parent',
                              'checked_in_by', 'checked_out_by', 'origin_transfer',)
              .defer("partner_organization",
                     "destination_point__point",
                     "destination_point__parent__parent",
                     "destination_point__parent__geom",
                     "destination_point__parent__point",
                     "origin_point__point",
                     "origin_point__parent__parent",
                     "origin_point__parent__geom",
                     "origin_point__parent__point"))
        if not handover:
            qs = qs.filter(partner_organization=partner)
        return qs

    def detail_qs(self):
        return self.get_queryset(handover=True).prefetch_related(
            Prefetch(
                'items', models.Item.objects
                .select_related('material')
                .prefetch_related('transfers_history')
                .annotate(description=F('material__short_description')))
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

        qs = self.get_queryset().filter(status=models.Transfer.PENDING)

        if location.poi_type.category == 'warehouse':
            qs = qs.filter(Q(destination_point=location) | Q(destination_point__isnull=True))
        else:
            qs = qs.filter(destination_point=location)

        qs = qs.exclude(origin_point=location).select_related("destination_point__parent", "origin_point__parent").order_by("-created")
        return self.paginate_response(qs)

    @action(detail=True, methods=['get'], url_path='details',
            serializer_class=serializers.TransferSerializer)
    def details(self, request, *args, **kwargs):
        transfer = self.get_object()
        serializer = self.serializer_class(transfer, context={'partner': request.user.partner})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='checked-in')
    def checked_in(self, request, *args, **kwargs):
        location = self.get_parent_poi()
        qs = self.get_queryset()\
            .filter(status=models.Transfer.COMPLETED, destination_point=location)\
            .exclude(origin_point=location).order_by("-created")

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='outgoing')
    def outgoing(self, request, *args, **kwargs):
        location = self.get_parent_poi()
        qs = self.get_queryset()\
            .filter(status=models.Transfer.PENDING, origin_point=location)\
            .exclude(destination_point=location).order_by("-created")

        return self.paginate_response(qs)

    @action(detail=False, methods=['get'], url_path='completed')
    def completed(self, request, *args, **kwargs):
        partner = self.request.user.partner
        location = self.get_parent_poi()
        completed_filters = Q()
        completed_filters |= Q(Q(origin_point=location) & ~Q(destination_point=location))
        completed_filters |= Q(destination_point=location,
                               transfer_type__in=[models.Transfer.WASTAGE, models.Transfer.DISPENSE])
        completed_filters |= Q(origin_point=location, transfer_type=models.Transfer.HANDOVER)
        qs = self.get_queryset(handover=True).filter(Q(status=models.Transfer.COMPLETED) | Q(from_partner_organization=partner)).filter(completed_filters).filter(
            Q(partner_organization=partner) | Q(from_partner_organization=partner)
        )
        if not self.request.query_params.get('transfer_type', None):
            qs = qs.exclude(transfer_type__in=[models.Transfer.WASTAGE])
        qs = qs.order_by("-created")
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

        return Response(serializers.TransferSerializer(serializer.instance, context={'partner': request.user.partner}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='mark-complete')
    def mark_complete(self, request, pk=None, **kwargs):
        raise PermissionDenied()
        # transfer = self.get_object()
        # if transfer.transfer_type == models.Transfer.DISTRIBUTION:
        #     transfer.status = models.Transfer.COMPLETED
        #
        # transfer.destination_check_in_at = timezone.now()
        # transfer.checked_in_by = request.user
        # transfer.save(update_fields=['status', 'destination_check_in_at', 'checked_in_by'])
        # return Response(serializers.TransferSerializer(transfer).data, status=status.HTTP_200_OK)

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

        return Response(serializers.TransferSerializer(serializer.instance, context={'partner': request.user.partner}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='upload-evidence',
            serializer_class=serializers.TransferEvidenceSerializer)
    def upload_evidence(self, request, **kwargs):
        transfer = self.get_object()
        if transfer.transfer_type != models.Transfer.WASTAGE:
            raise ValidationError(_('Evidence files are only for wastage transfers.'))

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(transfer=transfer, user=request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], serializer_class=serializers.TransferEvidenceListSerializer)
    def evidence(self, request, **kwargs):
        transfer = self.get_object()
        if transfer.transfer_type != models.Transfer.WASTAGE:
            raise ValidationError(_('Evidence files are only for wastage transfers.'))
        qs = transfer.transfer_evidences.all()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.serializer_class(qs, many=True).data)


class ItemUpdateViewSet(mixins.UpdateModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    queryset = models.Item.objects.all()
    serializer_class = serializers.ItemUpdateSerializer

    def get_queryset(self):
        # item must be associated to a transfer that belongs to the partner of the requesting user
        partner = self.request.user.partner
        if not partner:
            return super().get_queryset().none()
        return super().get_queryset().filter(transfer__partner_organization=partner)

    @action(detail=True, methods=['post'], serializer_class=serializers.ItemSplitSerializer)
    def split(self, request, **kwargs):
        item = self.get_object()

        serializer = self.serializer_class(instance=item, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_200_OK)


class PowerBIDataView(APIView):
    permission_classes = [IsIPLMEditor]

    @staticmethod
    def get_pbi_access_token():
        try:
            return get_access_token()
        except TokenRetrieveException:
            raise PermissionDenied('Token cannot be retrieved')

    @cached_property
    def pbi_headers(self):
        return {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.get_pbi_access_token()}

    def get(self, request, *args, **kwargs):
        try:
            embed_url, dataset_id = get_embed_url(self.pbi_headers)
            embed_token = get_embed_token(dataset_id, self.pbi_headers)
        except TokenRetrieveException:
            return Response("Temporary unavailable, PowerBI information cannot be retrieved from Microsoft Servers",
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        resp_data = {
            "report_id": settings.PBI_CONFIG["REPORT_ID"],
            "embed_url": embed_url,
            "access_token": embed_token,
            "vendor_number": request.user.profile.organization.vendor_number
        }
        return Response(resp_data, status=status.HTTP_200_OK)
