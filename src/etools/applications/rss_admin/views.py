import copy

from django.db import connection
# Field Monitoring imports for new features
from django.contrib.gis.geos import Point
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import Count

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
# openpyxl used for bulk site upload (reuse FM admin import logic)
import openpyxl
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.audit.filters import DisplayStatusFilter, EngagementFilter, UniqueIDOrderingFilter
from etools.applications.audit.models import Engagement
from etools.applications.audit.serializers.engagement import (
    AuditSerializer,
    EngagementListSerializer,
    MicroAssessmentSerializer,
    SpecialAuditSerializer,
    SpotCheckSerializer,
    StaffSpotCheckSerializer,
)
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.serializers import MonitoringActivitySerializer
from etools.applications.partners.filters import InterventionEditableByFilter, ShowAmendmentsFilter
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization, InterventionBudget
from etools.applications.organizations.models import Organization
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
)
from etools.libraries.djangolib.fields import CURRENCY_LIST
from etools.applications.partners.tasks import send_pd_to_vision
from etools.applications.partners.utils import send_agreement_suspended_notification
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import (
    AgreementRssSerializer,
    AnswerHactSerializer,
    BulkCloseProgrammeDocumentsSerializer,
    EngagementAttachmentsUpdateSerializer,
    EngagementChangeStatusSerializer,
    EngagementInitiationUpdateSerializer,
    EngagementLightRssSerializer,
    EngagementDetailRssSerializer,
    PartnerOrganizationRssSerializer,
    MapPartnerToWorkspaceSerializer,
    SetOnTrackSerializer,
    SitesBulkUploadSerializer,
)
from etools.applications.rss_admin.services import PartnerService, EngagementService, FieldMonitoringService
from etools.applications.rss_admin.importers import LocationSiteImporter
from etools.applications.rss_admin.validation import RssAgreementValid, RssInterventionValid
from etools.applications.utils.helpers import generate_hash
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.views import FilterQueryMixin
from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.action_points.serializers import ActionPointSerializer as APDetailSerializer, CommentSerializer as APCommentSerializer
from etools.applications.permissions2.views import PermittedSerializerMixin
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.audit.conditions import AuditModuleCondition


class PartnerOrganizationRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'organization__name',
        'organization__vendor_number',
        'organization__short_name',
        'email',
        'phone_number',
    )
    ordering_fields = (
        'organization__name', 'organization__vendor_number', 'rating', 'hidden'
    )

    # PMP-style filters mapping
    filters = (
        ('partner_types', 'organization__organization_type__in'),
        ('cso_types', 'organization__cso_type__in'),
        ('risk_ratings', 'rating__in'),
        ('rating', 'rating'),
        ('hidden', 'hidden'),
        ('organization__vendor_number', 'organization__vendor_number__icontains'),
    )

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_filter_queries(qs, self.filter_params)

    @action(detail=False, methods=['post'], url_path='map-to-workspace')
    def map_to_workspace(self, request, *args, **kwargs):
        """Map an existing Organization (by vendor number) as a Partner in the current workspace.

        If a PartnerOrganization already exists for the vendor number in this tenant, it is returned.
        Optionally updates lead_office/lead_section if provided.
        """
        payload = MapPartnerToWorkspaceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        vendor_number = payload.validated_data['vendor_number']
        lead_office = payload.validated_data.get('lead_office')
        lead_section = payload.validated_data.get('lead_section')

        partner, created = PartnerService.map_partner_to_workspace(
            vendor_number=vendor_number,
            lead_office=lead_office,
            lead_section=lead_section,
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(PartnerOrganizationRssSerializer(partner, context={'request': request}).data, status=status_code)


class AgreementRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Agreement.objects.all()
    serializer_class = AgreementRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'agreement_number',
        'partner__organization__name',
        'partner__organization__vendor_number',
    )
    ordering_fields = (
        'agreement_number', 'partner__organization__name', 'status', 'start', 'end'
    )

    # PMP-style filters mapping
    filters = (
        ('type', 'agreement_type__in'),
        ('types', 'agreement_type__in'),
        ('status', 'status__in'),
        ('statuses', 'status__in'),
        ('cpStructures', 'country_programme__in'),
        ('partners', 'partner__in'),
        ('start', 'start'),
        ('end', 'end'),
        ('special_conditions_pca', 'special_conditions_pca'),
    )

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_filter_queries(qs, self.filter_params)

    def perform_create(self, serializer):
        serializer.save()
        validator = RssAgreementValid(serializer.instance, user=self.request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

    def perform_update(self, serializer):
        old_instance = copy.copy(serializer.instance)
        serializer.save()
        validator = RssAgreementValid(
            serializer.instance,
            old=old_instance,
            user=self.request.user,
        )
        if not validator.is_valid:
            raise ValidationError(validator.errors)
        # notify on suspension
        if serializer.instance.status == serializer.instance.SUSPENDED and old_instance.status != serializer.instance.SUSPENDED:
            send_agreement_suspended_notification(serializer.instance, self.request.user)


class ProgrammeDocumentRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Intervention.objects.all()
    serializer_class = InterventionListSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        ShowAmendmentsFilter,
        InterventionEditableByFilter,
    )
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'number',
        'title',
        'agreement__agreement_number',
        'agreement__partner__organization__name',
        'agreement__partner__organization__vendor_number',
    )
    ordering_fields = (
        'number', 'document_type', 'status', 'title', 'start', 'end',
        'agreement__partner__organization__name'
    )

    filters = (
        ('status', 'status__in'),
        ('statuses', 'status__in'),
        ('document_type', 'document_type__in'),
        ('document_types', 'document_type__in'),
        ('sections', 'sections__in'),
        ('office', 'offices__in'),
        ('offices', 'offices__in'),
        ('donors', 'frs__fr_items__donor__icontains'),
        ('partners', 'agreement__partner__in'),
        ('grants', 'frs__fr_items__grant_number__icontains'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('budget_owner__in', 'budget_owner__in'),
        ('country_programme', 'country_programme__in'),
        ('country_programmes', 'country_programme__in'),
        ('cp_outputs', 'result_links__cp_output__in'),
        ('start', 'start'),
        ('end', 'end'),
        ('end_after', 'end__gte'),
        ('contingency_pd', 'contingency_pd'),
    )

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        if self.action == 'retrieve':
            return InterventionDetailSerializer
        return InterventionListSerializer

    def get_queryset(self):
        qs = Intervention.objects.frs_qs()
        return self.apply_filter_queries(qs, self.filter_params)

    def perform_create(self, serializer):
        serializer.save()
        validator = RssInterventionValid(serializer.instance, user=self.request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

    def perform_update(self, serializer):
        old_instance = copy.copy(serializer.instance)
        serializer.save()
        validator = RssInterventionValid(serializer.instance, old=old_instance, user=self.request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

    @action(detail=False, methods=['put'], url_path='bulk-close')
    def bulk_close(self, request, *args, **kwargs):
        serializer = BulkCloseProgrammeDocumentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.update(serializer.validated_data, request.user)
        return Response(result, status=status.HTTP_200_OK)

    def _apply_fr_numbers(self, data):
        """Minimal: allow 'fr_numbers' to map to 'frs' IDs for PATCH/PUT."""
        fr_numbers = data.get('fr_numbers')
        if fr_numbers is None:
            return data
        if not isinstance(fr_numbers, (list, tuple)):
            raise ValidationError({'fr_numbers': ["Must be a list of FR numbers"]})
        numbers = list(fr_numbers)
        qs = FundsReservationHeader.objects.filter(fr_number__in=numbers)
        found = list(qs.values_list('fr_number', flat=True))
        missing = [n for n in numbers if n not in found]
        if missing:
            raise ValidationError({'fr_numbers': [f"Unknown FR numbers: {', '.join(missing)}"]})
        new_data = data.copy()
        new_data['frs'] = list(qs.values_list('pk', flat=True))
        new_data.pop('fr_numbers', None)
        return new_data

    def update(self, request, *args, **kwargs):
        return self._update_with_fr_numbers(request, partial=False)

    def partial_update(self, request, *args, **kwargs):
        return self._update_with_fr_numbers(request, partial=True)

    def _update_with_fr_numbers(self, request, *, partial: bool):
        instance = self.get_object()
        payload = self._apply_fr_numbers(request.data)

        currency = payload.pop('currency', None)
        if currency is not None:
            if currency not in CURRENCY_LIST:
                return Response({'detail': f'Invalid currency: {currency}.'}, status=status.HTTP_400_BAD_REQUEST)
            InterventionBudget.objects.update_or_create(
                intervention=instance,
                defaults={'currency': currency},
            )

        serializer = self.get_serializer(instance=instance, data=payload, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        refreshed = Intervention.objects.select_related('planned_budget').get(pk=instance.pk)
        return Response(InterventionDetailSerializer(refreshed, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-frs')
    def assign_frs(self, request, pk=None):
        instance = self.get_object()
        frs = request.data.get('frs')
        if frs is None:
            return Response({'detail': 'Missing frs'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(frs, (list, tuple)):
            frs = [frs]

        serializer = InterventionCreateUpdateSerializer(
            instance=instance,
            data={'frs': frs},
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(InterventionDetailSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='set-currency')
    def set_currency(self, request, pk=None):
        instance = self.get_object()
        currency = request.data.get('currency')
        if not currency:
            return Response({'detail': 'Missing currency'}, status=status.HTTP_400_BAD_REQUEST)
        if currency not in CURRENCY_LIST:
            return Response({'detail': f'Invalid currency: {currency}.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            budget = instance.planned_budget
        except ObjectDoesNotExist:
            budget, _ = InterventionBudget.objects.get_or_create(intervention=instance)

        budget.currency = currency
        budget.save()
        return Response(InterventionDetailSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='send-to-vision')
    def send_to_vision(self, request, pk=None):
        instance = self.get_object()
        if tenant_switch_is_active('disable_pd_vision_sync'):
            return Response({'detail': 'Vision sync disabled by tenant switch'}, status=status.HTTP_403_FORBIDDEN)
        send_pd_to_vision.delay(connection.tenant.name, instance.pk)
        return Response({'detail': 'PD queued for Vision upload'}, status=status.HTTP_202_ACCEPTED)


class EngagementRssViewSet(PermittedSerializerMixin,
                           mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = Engagement.objects.all()
    serializer_class = EngagementLightRssSerializer
    permission_classes = (IsRssAdmin,)
    pagination_class = DynamicPageNumberPagination
    filter_backends = (
        SearchFilter,
        DisplayStatusFilter,
        DjangoFilterBackend,
        UniqueIDOrderingFilter,
        OrderingFilter,
    )
    search_fields = (
        'reference_number',
        'partner__organization__name',
        'partner__organization__vendor_number',
        'partner__organization__short_name',
        'agreement__auditor_firm__organization__name',
        'offices__name',
        '=id',
    )
    ordering_fields = (
        'agreement__order_number',
        'agreement__auditor_firm__organization__name',
        'partner__organization__name',
        'engagement_type',
        'status',
    )
    filterset_class = EngagementFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related('partner', 'agreement', 'agreement__auditor_firm__organization')
        return queryset

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(AuditModuleCondition())
        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.append(ObjectStatusCondition(obj))
        return context

    def get_serializer_class(self):
        # For list, use the default EngagementLightRssSerializer (permission-agnostic)
        if self.action == 'list':
            return EngagementLightRssSerializer
        if self.action == 'retrieve':
            instance = getattr(self, 'object', None)
            if not instance:
                try:
                    obj = self.get_object()
                except Exception:
                    return super().get_serializer_class()
            else:
                obj = instance

            serializer_cls = EngagementService.serializer_for_instance(obj)
            # RSS Admin: use permission-agnostic detail for audits
            if serializer_cls is AuditSerializer:
                return EngagementDetailRssSerializer
            if serializer_cls:
                return serializer_cls

        return super().get_serializer_class()

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        engagement = self.get_object()
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()
        serializer = EngagementChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        EngagementService.execute_action(
            engagement=engagement,
            action=action,
            send_back_comment=serializer.validated_data.get('send_back_comment'),
            cancel_comment=serializer.validated_data.get('cancel_comment'),
        )
        return Response(EngagementLightRssSerializer(engagement, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='initiation', url_name='initiation')
    def update_initiation(self, request, pk=None):
        """Update Engagement initiation data (FACE dates, totals, currency/exchange).

        Example payload keys: start_date, end_date, partner_contacted_at, total_value, exchange_rate, currency_of_report
        """
        engagement = self.get_object()
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()

        serializer = EngagementInitiationUpdateSerializer(
            instance=engagement,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(EngagementLightRssSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='attachments', url_name='attachments')
    def update_attachments(self, request, pk=None):
        """Attach uploaded files to the Engagement (financial assurance context).

        Payload accepts one or both keys: engagement_attachment (id) and report_attachment (id).
        """
        engagement = self.get_object()
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()

        serializer = EngagementAttachmentsUpdateSerializer(
            instance=engagement,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(EngagementLightRssSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

class ActionPointRssViewSet(viewsets.GenericViewSet):
    queryset = ActionPoint.objects.all()
    permission_classes = (IsRssAdmin,)
    serializer_class = APDetailSerializer

    @action(detail=True, methods=['post'], url_path='add-attachment')
    def add_attachment(self, request, pk=None):
        action_point = self.get_object()
        if not (action_point.high_priority and action_point.status == ActionPoint.STATUS_COMPLETED):
            return Response({'detail': 'Only completed high priority action points are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        comment_id = request.data.get('comment')
        attachment_id = request.data.get('supporting_document')

        if not comment_id or not attachment_id:
            return Response({'detail': 'Fields "comment" and "supporting_document" are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            comment = action_point.comments.get(pk=comment_id)
        except ActionPointComment.DoesNotExist:
            return Response({'detail': 'Comment not found for this Action Point.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = APCommentSerializer(
            instance=comment,
            data={'supporting_document': attachment_id},
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(APDetailSerializer(action_point, context={'request': request}).data, status=status.HTTP_200_OK)


class LocationSiteAdminViewSet(viewsets.ViewSet):
    permission_classes = (IsRssAdmin,)

    @staticmethod
    def _get_pcode(split_name, name):
        p_code = split_name[1].strip() if len(split_name) > 1 else None
        if not p_code or p_code == "None":
            return generate_hash(name, 12)
        return p_code

    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        serializer = SitesBulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload = serializer.validated_data['import_file']
        ok, result = LocationSiteImporter().import_file(upload)
        if not ok:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class MonitoringActivityRssViewSet(viewsets.ModelViewSet):
    queryset = MonitoringActivity.objects\
        .annotate(checklists_count=Count('checklists'))\
        .select_related('tpm_partner', 'tpm_partner__organization',
                        'visit_lead', 'location', 'location_site')\
        .prefetch_related('team_members', 'partners', 'partners__organization',
                          'report_reviewers', 'interventions', 'cp_outputs',
                          'sections', 'visit_goals', 'facility_types')\
        .order_by("-id")
    serializer_class = MonitoringActivitySerializer
    permission_classes = (IsRssAdmin,)
    pagination_class = DynamicPageNumberPagination
    filter_backends = (
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    )
    filterset_fields = {
        'monitor_type': ['exact'],
        'tpm_partner': ['exact', 'in'],
        'visit_lead': ['exact', 'in'],
        'location': ['exact', 'in'],
        'location_site': ['exact', 'in'],
        'start_date': ['gte', 'lte'],
        'end_date': ['gte', 'lte'],
        'status': ['exact', 'in'],
    }
    ordering_fields = (
        'start_date', 'end_date', 'location', 'location_site', 'monitor_type', 'checklists_count', 'status'
    )
    search_fields = ('number',)

    def get_serializer_class(self):
        from etools.applications.field_monitoring.planning.serializers import MonitoringActivityLightSerializer
        if self.action == 'list':
            return MonitoringActivityLightSerializer
        return MonitoringActivitySerializer

    @action(detail=True, methods=['post'], url_path='answer-hact')
    def answer_hact(self, request, pk=None):
        activity = self.get_object()
        serializer = AnswerHactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        partner = serializer.validated_data['partner']
        value = serializer.validated_data['value']

        aq_of = FieldMonitoringService.save_hact_answer(activity=activity, partner=partner, value=value)
        if not aq_of:
            return Response({'detail': 'No HACT question found for this activity and partner'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'detail': 'HACT answer saved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='set-on-track')
    def set_on_track(self, request, pk=None):
        activity = self.get_object()
        serializer = SetOnTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        partner = serializer.validated_data['partner']
        on_track = serializer.validated_data['on_track']

        aof = FieldMonitoringService.set_on_track(activity=activity, partner=partner, on_track=on_track)
        return Response({'detail': 'Monitoring status updated', 'on_track': aof.on_track}, status=status.HTTP_200_OK)
