from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_attachments.models import Attachment
from unicef_rest_export.renderers import ExportCSVRenderer, ExportOpenXMLRenderer
from unicef_rest_export.views import ExportMixin
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin, QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.core.mixins import GetSerializerClassMixin
from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.views.v2 import choices_to_json_ready
from etools.applications.permissions2.views import PermissionContextMixin, PermittedSerializerMixin
from etools.applications.travel.filters import ShowHiddenFilter
from etools.applications.travel.models import Activity, ItineraryItem, Report, Trip
from etools.applications.travel.permissions import trip_field_is_editable_permission, UserIsStaffPermission
from etools.applications.travel.serializers import (
    ActivityCreateUpdateSerializer,
    ActivityDetailSerializer,
    ItineraryItemSerializer,
    ItineraryItemUpdateSerializer,
    ReportAttachmentSerializer,
    ReportSerializer,
    TripAttachmentSerializer,
    TripCreateUpdateSerializer,
    TripCreateUpdateStatusSerializer,
    TripExportSerializer,
    TripSerializer,
    TripStatusHistorySerializer,
)
from etools.applications.travel.validation import TripValid


class TripViewSet(
        SafeTenantViewSetMixin,
        ValidatorViewMixin,
        QueryStringFilterMixin,
        ExportMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.DestroyModelMixin,
        PermittedSerializerMixin,
        viewsets.GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, UserIsStaffPermission]

    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter, ShowHiddenFilter)
    search_terms = [
        'reference_number__icontains',
        'title__icontains',
        'description__icontains',
        'supervisor__first_name__icontains',
        'supervisor__last_name__icontains',
        'traveller__first_name__icontains',
        'traveller__last_name__icontains',
        'section__name__icontains',
        'office__name__icontains']

    filters = (
        ('status', 'status__in'),
        ('traveller', 'traveller__in'),
        ('supervisor', 'supervisor__in'),
        ('office', 'office__in'),
        ('section', 'section__in'),
        ('partner', 'activities__partner__pk__in'),
        ('month', ['start_date__month',
                   'end_date__month']),
        ('year', ['start_date__year',
                  'end_date__year']),
        ('start_date', 'start_date'),
        ('end_date', 'end_date'),
        ('not_as_planned', 'not_as_planned')
    )
    export_filename = 'Trip'

    SERIALIZER_MAP = {
        "status_history": TripStatusHistorySerializer,
        "report": ReportSerializer
    }

    def parse_sort_params(self):
        SORT_BY = [
            "reference_number", "traveller",
            "office", "section", "start_date",
            "end_date", "status"
        ]
        sort_param = self.request.GET.get("sort")
        ordering = []
        if sort_param:
            sort_options = sort_param.split("|")
            for sort in sort_options:
                field, asc_desc = sort.split(".", 2)
                if asc_desc in ['asc', 'desc'] and field in SORT_BY:
                    ordering.append(f'{"-" if asc_desc == "desc" else ""}{field}')
        return ordering

    def get_queryset(self):
        qs = super().get_queryset()
        if "sort" in self.request.GET:
            qs = qs.order_by(*self.parse_sort_params())
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        self.serializer_class = TripCreateUpdateSerializer
        related_fields = []
        nested_related_names = []
        serializer = self.my_create(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs,
        )

        instance = serializer.instance

        validator = TripValid(instance, user=request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
        return Response(
            TripSerializer(
                instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if not kwargs.get("custom_serializer_class"):
            self.serializer_class = TripCreateUpdateSerializer
        related_fields = ["status_history", "report"]
        nested_related_names = ["attachments"]

        instance, old_instance, __ = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        validator = TripValid(
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
            TripSerializer(
                instance,
                context=self.get_serializer_context(),
            ).data
        )

    def perform_destroy(self, instance):
        if instance.status != Trip.STATUS_DRAFT:
            raise ValidationError(_("Only Draft Trips are allowed to be deleted."))
        super().perform_destroy(instance)

    def _set_status(self, request, trip_status):
        self.serializer_class = TripCreateUpdateStatusSerializer
        update_data = {
            "status": trip_status,
        }
        comment = request.data.get("comment")
        if comment:
            update_data["comment"] = comment
            if trip_status == Trip.STATUS_COMPLETED:
                update_data['not_as_planned'] = True

        request.data.clear()
        request.data.update(**update_data)
        request.data.update(
            {"status_history": [update_data]},
        )
        return self.update(request, partial=True, custom_serializer_class=True)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated,
                                                                UserIsStaffPermission,
                                                                trip_field_is_editable_permission("user_info_text")])
    def dismiss_infotext(self, request, pk=None):
        trip = self.get_object()
        try:
            trip.user_info_text.pop(request.data.get('code'))
        except KeyError:
            raise ValidationError("Message could not be found!")

        trip.save()
        return Response(
            TripSerializer(
                trip,
                context=self.get_serializer_context(),
            ).data
        )

    @action(detail=True, methods=["patch"])
    def revise(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_DRAFT)

    @action(detail=True, methods=["patch"])
    def subreview(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_SUBMISSION_REVIEW)

    @action(detail=True, methods=["patch"], url_name='submit-request-approval')
    def submit_request_approval(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_SUBMITTED)

    @action(detail=True, methods=["patch"], url_name='submit-no-approval')
    def submit_no_approval(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_APPROVED)

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_APPROVED)

    # @action(detail=True, methods=["patch"])
    # def review(self, request, pk=None):
    #     return self._set_status(request, Trip.STATUS_REVIEW)

    @action(detail=True, methods=["patch"])
    def complete(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_COMPLETED)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_CANCELLED)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        return self._set_status(request, Trip.STATUS_REJECTED)

    @action(
        detail=False,
        methods=['get'],
        url_path='export/xlsx',
        renderer_classes=(ExportOpenXMLRenderer,),
    )
    def list_export_xlsx(self, request, *args, **kwargs):
        self.serializer_class = TripExportSerializer
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
        self.serializer_class = TripExportSerializer
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
        self.serializer_class = TripExportSerializer
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
        self.serializer_class = TripExportSerializer
        serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })


class ItineraryItemViewSet(
        GetSerializerClassMixin,
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated,
                          IsReadAction | (IsEditAction & trip_field_is_editable_permission('itinerary_items'))]
    queryset = ItineraryItem.objects.all()
    serializer_class = ItineraryItemSerializer

    serializer_action_map = {
        "partial_update": ItineraryItemUpdateSerializer,
        "create": ItineraryItemUpdateSerializer
    }

    def perform_destroy(self, instance):
        if instance.monitoring_activity:
            raise ValidationError(_("Not allowed to delete an itinerary item generated by "
                                    "the addition of a monitoring activity, "
                                    "please remove the monitoring activity to automatically delete this item"))
        super().perform_destroy(instance)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(trip__pk=self.kwargs.get("nested_1_pk"))

    def get_root_object(self):
        """ returns parent object: method needed for the trip_field_is_editable_permission permissions class """
        return Trip.objects.get(pk=self.kwargs.get("nested_1_pk"))

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'trip': parent
        }


class TripAttachmentsViewSet(
        SafeTenantViewSetMixin,
        mixins.DestroyModelMixin,
        NestedViewSetMixin,
        viewsets.GenericViewSet,
):
    serializer_class = TripAttachmentSerializer
    queryset = Attachment.objects.all()
    permission_classes = [IsAuthenticated,
                          UserIsStaffPermission,
                          trip_field_is_editable_permission('attachments')]

    def get_view_name(self):
        return _('Related Documents')

    def get_root_object(self):
        return get_object_or_404(
            Trip,
            pk=self.kwargs.get("nested_1_pk"),
        )

    def get_parent_object(self):
        return get_object_or_404(
            Trip,
            pk=self.kwargs.get("nested_1_pk"),
        )

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {'code': 'travel_docs'}

        return {
            'content_type_id': ContentType.objects.get_for_model(Trip).pk,
            'object_id': parent.pk,
        }

    def get_object(self, pk=None):
        if pk:
            return self.queryset.get(pk=pk)
        return super().get_object()


class ActivityViewSet(
        GetSerializerClassMixin,
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        PermissionContextMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated,
                          IsReadAction | (IsEditAction & trip_field_is_editable_permission('itinerary_items'))]
    queryset = Activity.objects.all()
    serializer_class = ActivityDetailSerializer
    serializer_action_map = {
        "partial_update": ActivityCreateUpdateSerializer,
        "create": ActivityCreateUpdateSerializer
    }

    def update_ma_date(self, serializer):
        try:
            ma = MonitoringActivity.objects.get(id=serializer.initial_data['monitoring_activity'])
        except MonitoringActivity.DoesNotExist():
            raise ValidationError(_("Monitoring Activity not found"))
        serializer.initial_data['activity_date'] = ma.start_date

    @staticmethod
    def activity_type_fields_cleanup(serializer):
        _NULLABLE_FIELDS_MAP = {
            Activity.TYPE_PROGRAMME_MONITORING: ['partner', 'section', 'location'],
            Activity.TYPE_STAFF_DEVELOPMENT: ['partner', 'section', 'monitoring_activity'],
            Activity.TYPE_STAFF_ENTITLEMENT: ['partner', 'section', 'monitoring_activity'],
            Activity.TYPE_TECHNICAL_SUPPORT: ['partner', 'section', 'monitoring_activity'],
            Activity.TYPE_MEETING: ['monitoring_activity']
        }
        fields = _NULLABLE_FIELDS_MAP.get(serializer.initial_data['activity_type'])
        for field in fields:
            serializer.initial_data[field] = None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if 'activity_type' in serializer.initial_data and \
                serializer.initial_data['activity_type'] == Activity.TYPE_PROGRAMME_MONITORING:
            self.update_ma_date(serializer)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.initial_data['activity_type'] == Activity.TYPE_PROGRAMME_MONITORING:
            self.update_ma_date(serializer)

        self.activity_type_fields_cleanup(serializer)

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(trip__pk=self.kwargs.get("nested_1_pk"))

    def get_root_object(self):
        """ returns parent object: method needed for the trip_field_is_editable_permission permissions class """
        return Trip.objects.get(pk=self.kwargs.get("nested_1_pk"))

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'trip': parent
        }


class ReportViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Report.objects.all()
    serializer_class = ReportSerializer


class ReportAttachmentsViewSet(
        SafeTenantViewSetMixin,
        mixins.DestroyModelMixin,
        NestedViewSetMixin,
        viewsets.GenericViewSet,
):
    serializer_class = ReportAttachmentSerializer
    queryset = Attachment.objects.all()
    permission_classes = [IsAuthenticated,
                          UserIsStaffPermission,
                          trip_field_is_editable_permission('report')]

    def get_view_name(self):
        return _('Related Documents')

    def get_parent_object(self):
        return get_object_or_404(
            Report,
            trip__pk=self.kwargs.get("nested_1_pk"),
        )

    def get_root_object(self):
        return get_object_or_404(
            Trip,
            pk=self.kwargs.get("nested_1_pk"),
        )

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {'code': 'travel_report_docs'}

        return {
            'content_type_id': ContentType.objects.get_for_model(Report).pk,
            'object_id': parent.pk,
        }

    def get_object(self, pk=None):
        if pk:
            return self.queryset.get(pk=pk)
        return super().get_object()

    def perform_create(self, serializer):
        serializer.instance = self.get_object(
            pk=serializer.initial_data.get("id")
        )
        serializer.save(content_object=self.get_parent_object())

    def perform_update(self, serializer):
        serializer.save(content_object=self.get_parent_object())


class TravelStaticDropdownsListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        Return All Static values used for dropdowns in the frontend
        """

        activity_types = choices_to_json_ready(Activity.TYPE_CHOICES)
        travel_methods = choices_to_json_ready(ItineraryItem.METHOD_CHOICES)

        return Response(
            {
                'activity_types': activity_types,
                'travel_methods': travel_methods
            },
            status=status.HTTP_200_OK
        )
