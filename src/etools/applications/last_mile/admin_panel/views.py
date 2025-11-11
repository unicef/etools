from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import F, Prefetch, Q
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from unicef_rest_export.renderers import ExportCSVRenderer
from unicef_rest_export.views import ExportMixin
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES
from etools.applications.last_mile.admin_panel.csv_exporter import (
    LocationsCSVExporter,
    POITypesCSVExporter,
    UserAlertNotificationsCSVExporter,
    UserLocationsCSVExporter,
    UsersCSVExporter,
)
from etools.applications.last_mile.admin_panel.csv_importer import CsvImporter
from etools.applications.last_mile.admin_panel.filters import (
    AlertNotificationFilter,
    ItemFilter,
    LocationsFilter,
    TransferEvidenceFilter,
    TransferHistoryFilter,
    UserFilter,
    UserLocationsFilter,
)
from etools.applications.last_mile.admin_panel.serializers import (
    AlertNotificationCreateSerializer,
    AlertNotificationCustomeSerializer,
    AlertNotificationSerializer,
    AlertTypeSerializer,
    AuthUserPermissionsDetailSerializer,
    BulkReviewPointOfInterestSerializer,
    BulkReviewTransferSerializer,
    BulkUpdateLastMileProfileStatusSerializer,
    ImportFileSerializer,
    ItemStockManagementUpdateSerializer,
    ItemTransferAdminSerializer,
    LastMileUserProfileSerializer,
    LastMileUserProfileUpdateAdminSerializer,
    LocationBorderResponseSerializer,
    LocationsAdminSerializer,
    MaterialAdminSerializer,
    OrganizationAdminSerializer,
    PartnerOrganizationAdminSerializer,
    PointOfInterestAdminSerializer,
    PointOfInterestCoordinateAdminSerializer,
    PointOfInterestCustomSerializer,
    PointOfInterestExportSerializer,
    PointOfInterestLightSerializer,
    PointOfInterestTypeAdminSerializer,
    PointOfInterestWithCoordinatesSerializer,
    TransferHistoryAdminSerializer,
    TransferItemAdminSerializer,
    TransferItemCreateSerializer,
    TransferLogAdminSerializer,
    TransferReverseAdminSerializer,
    UserAdminCreateSerializer,
    UserAdminExportSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
    UserAlertNotificationsExportSerializer,
    UserPointOfInterestAdminSerializer,
    UserPointOfInterestExportSerializer,
    ValidateBorderSerializer,
)
from etools.applications.last_mile.admin_panel.services.location_validator import LocationValidatorService
from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.permissions import IsLMSMAdmin
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Group, Realm


class UserViewSet(ExportMixin,
                  mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    permission_classes = [IsLMSMAdmin]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        schema_name = connection.tenant.schema_name
        User = get_user_model()

        points_of_interest_prefetch = Prefetch(
            'points_of_interest',
            queryset=models.UserPointsOfInterest.objects.select_related(
                'point_of_interest',
                'point_of_interest__parent',
                'point_of_interest__poi_type',
                'user'
            )
        )

        realms_prefetch = Prefetch(
            'realms',
            queryset=Realm.objects.filter(
                is_active=True,
                country__schema_name=schema_name,
                group__name__in=ALERT_TYPES.keys()
            ).select_related('group')
        )

        created_by_prefetch = Prefetch(
            'last_mile_profile__created_by',
            queryset=User.objects.only('id', 'first_name', 'middle_name', 'last_name', 'is_active')
        )

        approved_by_prefetch = Prefetch(
            'last_mile_profile__approved_by',
            queryset=User.objects.only('id', 'first_name', 'middle_name', 'last_name', 'is_active')
        )

        queryset = User.objects.select_related(
            'profile',
            'profile__country',
            'profile__organization',
            'profile__organization__partner',
            'last_mile_profile',
        ).prefetch_related(
            realms_prefetch,
            points_of_interest_prefetch,
            created_by_prefetch,
            approved_by_prefetch,
        ).annotate(profile_status=F('last_mile_profile__status')).for_schema(schema_name).only_lmsm_users()

        has_active_location = self.request.query_params.get('hasActiveLocation')
        if has_active_location == "1":
            queryset = queryset.with_points_of_interest()
        elif has_active_location == "0":
            queryset = queryset.without_points_of_interest()

        show_all_users = self.request.query_params.get('showAllUsers')
        if show_all_users != "1":
            queryset = queryset.non_unicef_users()

        return queryset.distinct()

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = ('email', 'first_name', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number')
    filterset_class = UserFilter
    ordering_fields = [
        'id',
        'email',
        'is_active',
        'last_login',
        'first_name',
        'last_name',
        'profile_status',
        'profile__organization__name',
        'profile__organization__vendor_number',
        'profile__country__name',
        'profile__country__id',
        'profile__organization__partner__points_of_interest__name',
    ]

    ordering = ('id',)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['country_schema'] = connection.tenant.schema_name
        return context

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update']:
            return UserAdminUpdateSerializer
        if self.action == 'create':
            return UserAdminCreateSerializer
        if self.action == 'list_export_csv':
            return UserAdminExportSerializer
        if self.action == '_import_file':
            return ImportFileSerializer
        return UserAdminSerializer

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = StreamingHttpResponse(
            UsersCSVExporter().generate_csv_data(queryset=queryset, serializer_class=self.get_serializer_class()),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="users_{timezone.now().date()}.csv"'

        return response

    @action(detail=False, methods=['post'], url_path='import/xlsx')
    def _import_file(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        excel_file = serializer.validated_data['file']
        valid, out = CsvImporter().import_users(excel_file, connection.tenant.schema_name, request.user)
        if not valid:
            resp = HttpResponse(out.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="checked_{excel_file.name}"'
            return resp
        return Response({"valid": valid}, status=status.HTTP_200_OK)


class UpdateUserProfileViewSet(mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin,
                               viewsets.GenericViewSet):
    permission_classes = [IsLMSMAdmin]

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update']:
            return LastMileUserProfileUpdateAdminSerializer
        return LastMileUserProfileSerializer

    def get_queryset(self):
        schema_name = connection.tenant.schema_name
        User = get_user_model()
        return User.objects.for_schema(schema_name)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['country_schema'] = connection.tenant.schema_name
        return context

    @action(detail=False, methods=['patch'], url_path='bulk')
    def bulk_update(self, request, *args, **kwargs):
        serializer_data = BulkUpdateLastMileProfileStatusSerializer(data=request.data)
        serializer_data.is_valid(raise_exception=True)
        serializer_data.update(serializer_data.validated_data, request.user)
        return Response(serializer_data.data, status=status.HTTP_200_OK)


class LocationsViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """
    GeoJSON representation of a geographical point.

    This object adheres to the GeoJSON standard, where:
    - "type" specifies the kind of geometry (e.g., "Point")
    - "coordinates" is a list containing the longitude and latitude values.

    Example:
        {
            "type": "Point",
            "coordinates": [43.713459135964513, 25.589650059118867]
        }
    """
    permission_classes = [IsLMSMAdmin]
    serializer_class = PointOfInterestAdminSerializer
    pagination_class = DynamicPageNumberPagination
    adminValidator = AdminPanelValidator()

    queryset = models.PointOfInterest.all_objects.select_related(
        "parent",
        "poi_type",
        "secondary_type",
        "parent__parent",
        "parent__parent__parent",
        "parent__parent__parent__parent"
    ).annotate(
        region=F('parent__parent__name'),
        district=F('parent__parent__parent__name'),
        country=F('parent__name')
    ).prefetch_related(
        'partner_organizations',
        'partner_organizations__organization',
        'destination_transfers'
    ).all().order_by('id')

    def get_queryset(self):
        organization_id = self.request.query_params.get('organization_id')
        if organization_id:
            self.adminValidator.validate_organization_id(organization_id)
            self.queryset = self.queryset.filter(partner_organizations__organization__id=organization_id)
        if self.request.query_params.get('with_coordinates') is None:
            self.queryset = self.queryset.defer(
                'parent__point',
                'parent__parent__point',
                'parent__parent__parent__point',
                'parent__parent__parent__parent__point',
                'parent__geom',
                'parent__parent__geom',
                'parent__parent__parent__geom',
                'parent__parent__parent__parent__geom'
            )
        return self.queryset

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = LocationsFilter

    ordering_fields = [
        'id',
        'poi_type',
        'secondary_type',
        'country',
        'p_code',
        'description',
        'region',
        'district',
        'name',
    ]
    search_fields = ('name',
                     'p_code',
                     'partner_organizations__organization__name',
                     'partner_organizations__organization__vendor_number',
                     'destination_transfers__name',
                     'destination_transfers__unicef_release_order',
                     'destination_transfers__items__mapped_description',
                     'destination_transfers__items__material__short_description',
                     'destination_transfers__items__material__number')

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update', 'create']:
            return PointOfInterestCustomSerializer
        if self.request.query_params.get('with_coordinates') is not None:
            return PointOfInterestWithCoordinatesSerializer
        if self.action == 'list_export_csv':
            return PointOfInterestExportSerializer
        if self.action == 'bulk_review':
            return BulkReviewPointOfInterestSerializer
        if self.action == '_import_file':
            return ImportFileSerializer
        if self.action == 'validate_border':
            return ValidateBorderSerializer
        return PointOfInterestAdminSerializer

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        only_locations = self.request.query_params.get('only_locations', False)
        queryset = self.filter_queryset(self.get_queryset())
        response = StreamingHttpResponse(
            LocationsCSVExporter().generate_csv_data(queryset=queryset, serializer_class=self.get_serializer_class(), only_locations=only_locations),
            content_type='text/csv'
        )
        if only_locations:
            response['Content-Disposition'] = f'attachment; filename="locations_{timezone.now()}.csv"'
        else:
            response['Content-Disposition'] = f'attachment; filename="stock_management_locations_{timezone.now()}.csv"'
        return response

    @action(detail=False, methods=['post'], url_path='import/xlsx')
    def _import_file(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        excel_file = serializer.validated_data['file']
        valid, out = CsvImporter().import_locations(excel_file, request.user)
        if not valid:
            resp = HttpResponse(out.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="checked_{excel_file.name}"'
            return resp
        return Response({"valid": valid}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='validate-border')
    def validate_border(self, request, *args, **kwargs):
        serializer = ValidateBorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        point = serializer.validated_data.get('point')

        validator_service = LocationValidatorService()
        result = validator_service.validate_point_with_borders(point)

        if result['valid']:
            response_serializer = LocationBorderResponseSerializer(result['location'])
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response({
            "valid": False,
            "error": result.get('error', 'No location found for the provided coordinates')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put'], url_path='bulk-review')
    def bulk_review(self, request, *args, **kwargs):
        serializer_data = BulkReviewPointOfInterestSerializer(data=request.data)
        serializer_data.is_valid(raise_exception=True)
        serializer_data.update(serializer_data.validated_data, request.user)
        return Response(serializer_data.data, status=status.HTTP_200_OK)


class PointOfInterestsLightViewSet(mixins.ListModelMixin,
                                   mixins.RetrieveModelMixin,
                                   viewsets.GenericViewSet):
    permission_classes = [IsLMSMAdmin]
    serializer_class = PointOfInterestLightSerializer
    pagination_class = DynamicPageNumberPagination

    queryset = models.PointOfInterest.all_objects.select_related(
        'parent',
        'parent__parent',
        'parent__parent__parent',
        'parent__parent__parent__parent'
    ).only(
        "parent__name",
        "id",
        "name",
        "point",
        "parent__admin_level",
        "parent__parent__name",
        "parent__parent__admin_level",
        "parent__parent__parent__name",
        "parent__parent__parent__admin_level",
        "parent__parent__parent__parent__name",
        "parent__parent__parent__parent__admin_level").prefetch_related('partner_organizations').all().order_by('id')


class UserLocationsViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           GenericViewSet):
    permission_classes = [IsLMSMAdmin]
    serializer_class = UserPointOfInterestAdminSerializer
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        base_qs = get_user_model().objects.for_schema(connection.tenant.schema_name).distinct().order_by('id')

        if self.action not in ['update', 'partial_update', 'retrieve']:
            return base_qs.filter(profile__organization__partner__points_of_interest__isnull=False)
        return base_qs

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = UserLocationsFilter

    ordering_fields = [
        'first_name',
        'email',
        'last_name',
        'profile__organization__name',
        'profile__organization__vendor_number',
        'profile__organization__partner__points_of_interest__name'
    ]

    def get_serializer_class(self):
        if self.action == 'list_export_csv':
            return UserPointOfInterestExportSerializer
        return UserPointOfInterestAdminSerializer

    search_fields = ('first_name', 'email', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number', 'profile__organization__partner__points_of_interest__name')

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = StreamingHttpResponse(
            UserLocationsCSVExporter().generate_csv_data(queryset=queryset, serializer_class=self.get_serializer_class()),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="user_locations_{timezone.now().date()}.csv"'
        return response


class AlertNotificationViewSet(mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.DestroyModelMixin,
                               GenericViewSet):

    permission_classes = [IsLMSMAdmin]
    serializer_class = AlertNotificationSerializer
    pagination_class = DynamicPageNumberPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ALERT_TYPES'] = ALERT_TYPES
        context['country_schema'] = connection.tenant.schema_name
        return context

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update', 'delete']:
            return AlertNotificationCustomeSerializer
        if self.action == 'create':
            return AlertNotificationCreateSerializer
        if self.action == "list_export_csv":
            return UserAlertNotificationsExportSerializer
        return AlertNotificationSerializer

    def get_queryset(self):
        if self.action in ["list", "list_export_csv"]:
            # Use prefetch_related instead of annotate to avoid GROUP BY issues
            return (
                get_user_model().objects.filter(
                    realms__country__schema_name=connection.tenant.schema_name,
                    realms__is_active=True,
                    realms__group__name__in=ALERT_TYPES.keys()
                )
                .prefetch_related(
                    Prefetch(
                        'realms',
                        queryset=Realm.objects.filter(
                            country__schema_name=connection.tenant.schema_name,
                            is_active=True,
                            group__name__in=ALERT_TYPES.keys()
                        ).select_related('group')
                    )
                )
                .distinct()
                .order_by('id')
            )
        return Realm.objects.filter(country__schema_name=connection.tenant.schema_name, group__name__in=ALERT_TYPES.keys()).distinct().order_by('id')

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    @property
    def filterset_class(self):
        if self.action in ['list', 'list_export_csv']:
            return AlertNotificationFilter
        return None

    @property
    def ordering_fields(self):
        if self.action in ['list', 'list_export_csv']:
            return ['email', 'first_name', 'last_name']
        return []

    @property
    def search_fields(self):
        if self.action in ['list', 'list_export_csv']:
            return ('email', 'first_name', 'last_name')
        return []

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = StreamingHttpResponse(
            UserAlertNotificationsCSVExporter().generate_csv_data(queryset=queryset, serializer_class=self.get_serializer_class()),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="email_alerts_{timezone.now().date()}.csv"'
        return response


class TransferItemViewSet(mixins.ListModelMixin, GenericViewSet, mixins.CreateModelMixin):
    permission_classes = [IsLMSMAdmin]
    serializer_class = ItemTransferAdminSerializer
    pagination_class = DynamicPageNumberPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = ItemFilter
    search_fields = (
        'mapped_description',
        'material__short_description',
        'material__number',
        'transfer__name',
        'transfer__unicef_release_order',
        'uom',
        'batch_id',
        'material__original_uom'
    )

    ordering_fields = (
        'mapped_description',
        'material__short_description',
        'material__number',
        'transfer__name',
        'transfer__unicef_release_order',
        'uom',
        'batch_id',
        'material__original_uom',
        'quantity',
        'expiry_date',
        'last_updated'
    )

    def get_queryset(self):
        poi_id = self.request.query_params.get('poi_id')

        if not poi_id:
            raise ValidationError({'poi_id': 'This query parameter is required.'})

        return models.Item.objects.select_related(
            'material',
            'transfer',
            'transfer__destination_point',
            'transfer__origin_point'
        ).filter(
            transfer__destination_point_id=poi_id
        ).annotate(
            last_updated=F('modified'),
        ).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'create':
            return TransferItemCreateSerializer
        if self.action == "_import_file":
            return ImportFileSerializer
        if self.action == 'bulk_review':
            return BulkReviewTransferSerializer
        return ItemTransferAdminSerializer

    @action(detail=False, methods=['post'], url_path='import/xlsx')
    def _import_file(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        excel_file = serializer.validated_data['file']
        valid, out = CsvImporter().import_stock(excel_file, request.user)
        if not valid:
            resp = HttpResponse(out.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="checked_{excel_file.name}"'
            return resp
        return Response({"valid": valid}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='bulk-review')
    def bulk_review(self, request, *args, **kwargs):
        serializer_data = BulkReviewTransferSerializer(data=request.data)
        serializer_data.is_valid(raise_exception=True)
        serializer_data.update(serializer_data.validated_data, request.user)
        return Response(serializer_data.data, status=status.HTTP_200_OK)


class ItemStockManagementView(mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    permission_classes = [IsLMSMAdmin]
    serializer_class = ItemStockManagementUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.hide()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        return models.Item.objects.all()


class OrganizationListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = OrganizationAdminSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Organization.objects.all() \
            .select_related('partner', 'auditorfirm', 'tpmpartner') \
            .prefetch_related('auditorfirm__purchase_orders', 'tpmpartner__countries')

        with_partner = Q(partner__isnull=False, partner__hidden=False)

        with_audit = Q(auditorfirm__purchase_orders__engagement__isnull=False, auditorfirm__hidden=False)

        with_tpm = Q(tpmpartner__countries=connection.tenant, tpmpartner__hidden=False)

        return queryset.filter(with_partner | with_audit | with_tpm).distinct()

    filter_backends = (SearchFilter,)

    search_fields = ('name', 'vendor_number')


class ParentLocationListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = LocationsAdminSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return Location.objects.all().order_by('id')


class PointOfInterestTypeListView(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    serializer_class = PointOfInterestTypeAdminSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return models.PointOfInterestType.objects.all().order_by('id')

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = StreamingHttpResponse(
            POITypesCSVExporter().generate_csv_data(queryset=queryset, serializer_class=self.get_serializer_class()),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="locations_type_{timezone.now().date()}.csv"'
        return response


class PointOfInterestCoordinateListView(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = PointOfInterestCoordinateAdminSerializer
    permission_classes = [IsLMSMAdmin]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        return models.PointOfInterest.objects.all().order_by('id')


class AlertTypeListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = AlertTypeSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return Group.objects.filter(name__in=ALERT_TYPES.keys()).order_by('id')


class TransferHistoryListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = TransferHistoryAdminSerializer
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsLMSMAdmin]

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    filterset_class = TransferHistoryFilter

    ordering_fields = ['unicef_release_order', 'transfer_name', 'transfer_type', 'status', 'partner_organization', 'destination_point', 'origin_point']
    search_fields = ['unicef_release_order',
                     'transfer_name',
                     'transfer_type',
                     'status',
                     'partner_organization',
                     'destination_point',
                     'origin_point',
                     # Sub Transfers Search
                     'transfers__unicef_release_order',
                     'transfers__name',
                     'transfers__transfer_type',
                     'transfers__status',
                     'transfers__partner_organization__organization__name',
                     'transfers__destination_point__name',
                     'transfers__origin_point__name']

    def get_queryset(self):
        transfers_prefetch = Prefetch(
            'transfers',
            queryset=models.Transfer.objects.select_related(
                'partner_organization__organization',
                'destination_point',
                'origin_point'
            ).only(
                'id',
                'unicef_release_order',
                'name',
                'transfer_type',
                'status',
                'partner_organization__id',
                'partner_organization__organization__id',
                'partner_organization__organization__name',
                'destination_point__id',
                'destination_point__name',
                'origin_point__id',
                'origin_point__name',
                'transfer_history_id'
            )
        )

        qs = models.TransferHistory.objects.select_related(
            'origin_transfer',
            'origin_transfer__partner_organization__organization',
            'origin_transfer__destination_point',
            'origin_transfer__origin_point'
        ).prefetch_related(
            transfers_prefetch
        ).annotate(
            unicef_release_order=F('origin_transfer__unicef_release_order'),
            transfer_name=F('origin_transfer__name'),
            transfer_type=F('origin_transfer__transfer_type'),
            status=F('origin_transfer__status'),
            partner_organization=F('origin_transfer__partner_organization__organization__name'),
            destination_point=F('origin_transfer__destination_point__name'),
            origin_point=F('origin_transfer__origin_point__name')
        ).only(
            'id',
            'created',
            'modified',
            'origin_transfer__id',
            'origin_transfer__unicef_release_order',
            'origin_transfer__name',
            'origin_transfer__transfer_type',
            'origin_transfer__status',
            'origin_transfer__partner_organization__id',
            'origin_transfer__partner_organization__organization__id',
            'origin_transfer__partner_organization__organization__name',
            'origin_transfer__destination_point__id',
            'origin_transfer__destination_point__name',
            'origin_transfer__origin_point__id',
            'origin_transfer__origin_point__name'
        ).order_by('-created').distinct()

        return qs


class TransferEvidenceListView(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsLMSMAdmin]
    serializer_class = TransferLogAdminSerializer
    pagination_class = DynamicPageNumberPagination
    lookup_field = 'transfer_history_id'

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    filterset_class = TransferEvidenceFilter

    search_fields = ['unicef_release_order',
                     'name',
                     'transfer_type',
                     'status',
                     'partner_organization__organization__name',
                     'from_partner_organization__organization__name',
                     'recipient_partner_organization__organization__name',
                     'destination_point__name',
                     'origin_point__name']

    def get_queryset(self):
        return models.Transfer.objects.all()

    def retrieve(self, request, *args, **kwargs):
        transfer_history_id = self.kwargs.get(self.lookup_field)
        queryset = models.Transfer.objects.select_related(
            'from_partner_organization__organization',
            'recipient_partner_organization__organization',
            'partner_organization__organization',
            'origin_point',
            'destination_point'
        ).filter(transfer_history_id=transfer_history_id, items__isnull=False).only(
            'id',
            'created',
            'modified',
            'unicef_release_order',
            'name',
            'transfer_type',
            'transfer_subtype',
            'status',
            'origin_point__name',
            'origin_point',
            'destination_point__name',
            'destination_point',
            'from_partner_organization__organization__name',
            'recipient_partner_organization__organization__name',
            'partner_organization__organization__name'
        ).distinct()
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    class Meta:
        model = models.Transfer
        lookup_field = 'origin_transfer_id'


class MaterialListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = MaterialAdminSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return models.Material.objects.all().order_by('id')


class PartnerOrganizationListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = PartnerOrganizationAdminSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return PartnerOrganization.objects.all().order_by('id')


class UserPermissionsListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = AuthUserPermissionsDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_user_model().objects.filter(pk=self.request.user.pk)


class TransferReverseView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = TransferItemAdminSerializer
    serializer_class_reverse = TransferReverseAdminSerializer
    permission_classes = [IsLMSMAdmin]

    def get_queryset(self):
        return models.Transfer.objects.prefetch_related("items__material").all()

    def get_object(self):
        transfer_id = self.kwargs.get('pk')
        return get_object_or_404(self.get_queryset(), pk=transfer_id)

    def get_serializer_class(self):
        if self.action == 'reverse':
            return self.serializer_class_reverse
        return self.serializer_class

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, *args, **kwargs):
        transfer = self.get_object()
        serializer = self.serializer_class(transfer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='reverse')
    def reverse(self, request, pk=None):
        transfer = self.get_object()
        serializer = self.get_serializer(transfer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
