from django.db import transaction
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_rest_export.renderers import ExportCSVRenderer, ExportOpenXMLRenderer
from unicef_rest_export.views import ExportMixin
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin, QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import NestedPermission
from etools.applications.permissions2.metadata import PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedSerializerMixin
from etools.applications.travel.conditions import TravelModuleCondition
from etools.applications.travel.models import Itinerary, ItineraryActionPoint
from etools.applications.travel.renderers import ItineraryActionPointCSVRenderer
from etools.applications.travel.serializers import (
    ItineraryActionPointExportSerializer,
    ItineraryActionPointSerializer,
    ItineraryExportSerializer,
    ItinerarySerializer,
    ItineraryStatusHistorySerializer,
    ItineraryStatusSerializer,
)
from etools.applications.travel.validation import ItineraryValid


class ItineraryViewSet(
        SafeTenantViewSetMixin,
        ValidatorViewMixin,
        QueryStringFilterMixin,
        ExportMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        PermittedSerializerMixin,
        viewsets.GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    queryset = Itinerary.objects.all()
    serializer_class = ItinerarySerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    filters = (
        ('q', [
            'reference_number__icontains',
            'supervisor__first_name__icontains',
            'supervisor__user__last_name__icontains',
            'traveller__first_name__icontains',
            'traveller__last_name__icontains',
        ]),
        ('status', 'status__in'),
        ('start_date', 'start_date'),
        ('end_date', 'end_date'),
    )
    export_filename = 'Itinerary'

    SERIALIZER_MAP = {
        "status_history": ItineraryStatusHistorySerializer,
    }

    def parse_sort_params(self):
        MAP_SORT = {
            "reference_number": "reference_number",
        }
        sort_param = self.request.GET.get("sort")
        ordering = []
        if sort_param:
            sort_options = sort_param.split("|")
            for sort in sort_options:
                field, asc_desc = sort.split(".", 2)
                if field in MAP_SORT:
                    ordering.append(
                        "{}{}".format(
                            "-" if asc_desc == "desc" else "",
                            MAP_SORT[field],
                        )
                    )
        return ordering

    def get_queryset(self):
        qs = super().get_queryset()
        if "sort" in self.request.GET:
            qs = qs.order_by(*self.parse_sort_params())
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        related_fields = []
        nested_related_names = []
        serializer = self.my_create(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs,
        )

        instance = serializer.instance

        validator = ItineraryValid(instance, user=request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
        return Response(
            ItinerarySerializer(
                instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ["status_history"]
        nested_related_names = []

        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        validator = ItineraryValid(
            instance,
            old=old_instance,
            user=request.user,
        )
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(
            ItinerarySerializer(
                instance,
                context=self.get_serializer_context(),
            ).data
        )

    def _set_status(self, request, itinerary_status):
        self.serializer_class = ItineraryStatusSerializer
        status = {
            "status": itinerary_status,
        }
        comment = request.data.get("comment")
        if comment:
            status["comment"] = comment
        request.data.clear()
        request.data.update({"status": itinerary_status})
        request.data.update(
            {"status_history": [status]},
        )
        return self.update(request, partial=True)

    @action(detail=True, methods=["patch"])
    def revise(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_DRAFT)

    @action(detail=True, methods=["patch"])
    def subreview(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_SUBMISSION_REVIEW)

    @action(detail=True, methods=["patch"])
    def submit(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_SUBMITTED)

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_APPROVED)

    @action(detail=True, methods=["patch"])
    def review(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_REVIEW)

    @action(detail=True, methods=["patch"])
    def completed(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_COMPLETED)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_CANCELLED)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        return self._set_status(request, Itinerary.STATUS_REJECTED)

    @action(
        detail=False,
        methods=['get'],
        url_path='export/xlsx',
        renderer_classes=(ExportOpenXMLRenderer,),
    )
    def list_export_xlsx(self, request, *args, **kwargs):
        self.serializer_class = ItineraryExportSerializer
        itineraries = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(itineraries, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=itineraries_{}.xlsx'.format(
                timezone.now().date(),
            )
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='export/xlsx',
        renderer_classes=(ExportOpenXMLRenderer,),
    )
    def single_export_xlsx(self, request, *args, **kwargs):
        self.serializer_class = ItineraryExportSerializer
        serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.xlsx'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        self.serializer_class = ItineraryExportSerializer
        itineraries = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(itineraries, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=itineraries_{}.csv'.format(
                timezone.now().date(),
            )
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def single_export_csv(self, request, *args, **kwargs):
        self.serializer_class = ItineraryExportSerializer
        serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })


class ItineraryActionPointViewSet(
        SafeTenantViewSetMixin,
        PermittedSerializerMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        NestedViewSetMixin,
        viewsets.GenericViewSet,
):
    metadata_class = PermissionBasedMetadata
    queryset = ItineraryActionPoint.objects.all()
    serializer_class = ItineraryActionPointSerializer
    permission_classes = [IsAuthenticated, NestedPermission]

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(TravelModuleCondition())
        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
        ])
        return context

    @action(
        detail=False,
        methods=['get'],
        url_path='export',
        renderer_classes=(ItineraryActionPointCSVRenderer,),
    )
    def csv_export(self, request, *args, **kwargs):
        serializer = ItineraryActionPointExportSerializer(
            self.filter_queryset(self.get_queryset()),
            many=True,
        )
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_action_points_{}.csv'.format(
                self.get_root_object().reference_number, timezone.now().date()
            )
        })
