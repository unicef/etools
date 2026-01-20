import copy

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import Count, Prefetch

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from unicef_attachments.models import Attachment
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin, QueryStringFilterMixin

from etools.applications.action_points.filters import RelatedModuleFilter
from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.action_points.serializers import CommentSerializer as APCommentSerializer
from etools.applications.audit.conditions import AuditModuleCondition
from etools.applications.audit.filters import DisplayStatusFilter, EngagementFilter, UniqueIDOrderingFilter
from etools.applications.audit.models import Engagement
from etools.applications.audit.serializers.engagement import EngagementAttachmentSerializer, ReportAttachmentSerializer
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
    Finding,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.serializers import (
    MonitoringActivityLightSerializer,
    MonitoringActivitySerializer,
)
from etools.applications.rss_admin.filters import MonitoringActivityRssFilterSet
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.partners.filters import (
    InterventionEditableByFilter,
    PartnerNameOrderingFilter,
    ShowAmendmentsFilter,
)
from etools.applications.partners.models import Agreement, Intervention, InterventionBudget, PartnerOrganization
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
)
from etools.applications.partners.tasks import send_pd_to_vision
from etools.applications.partners.utils import send_agreement_suspended_notification
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.views import PermittedSerializerMixin
from etools.applications.rss_admin.admin_logging import extract_requested_changes, get_changed_fields, log_change
from etools.applications.rss_admin.importers import LocationSiteImporter
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import (
    ActionPointRssDetailSerializer,
    ActionPointRssListSerializer,
    ActivityOverallFindingRssSerializer,
    ActivityQuestionOverallFindingRssSerializer,
    AgreementRssSerializer,
    AnswerHactSerializer,
    AuditRssSerializer as AuditSerializer,
    BulkCloseProgrammeDocumentsSerializer,
    EngagementAttachmentsUpdateSerializer,
    EngagementChangeStatusSerializer,
    EngagementInitiationUpdateSerializer,
    EngagementLightRssSerializer,
    LogEntrySerializer,
    MapPartnerToWorkspaceSerializer,
    MicroAssessmentRssSerializer as MicroAssessmentSerializer,
    PartnerOrganizationRssSerializer,
    SetOnTrackSerializer,
    SitesBulkUploadSerializer,
    SpecialAuditRssSerializer as SpecialAuditSerializer,
    SpotCheckRssSerializer as SpotCheckSerializer,
    StaffSpotCheckRssSerializer as StaffSpotCheckSerializer,
)
from etools.applications.rss_admin.services import EngagementService, FieldMonitoringService, PartnerService
from etools.applications.rss_admin.validation import RssAgreementValid, RssInterventionValid
from etools.applications.utils.helpers import generate_hash
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.fields import CURRENCY_LIST
from etools.libraries.djangolib.views import FilterQueryMixin


class AdminLogEntriesMixin:
    """Helpers for @action(detail=True) admin logs endpoints.

    Notes:
    - Some viewsets use `AppendablePageNumberPagination` which disables pagination unless `?page=` is provided.
      To keep the API response stable, we return a paginated-shaped payload even when pagination is not applied.
    """

    def _get_admin_log_entries(self, obj):
        if hasattr(obj, 'get_subclass'):
            obj = obj.get_subclass()

        content_type = ContentType.objects.get_for_model(obj.__class__)
        return LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(obj.pk),
        ).select_related('user', 'content_type').order_by('-action_time')

    def _paginate_and_respond_consistently(self, queryset, serializer_class):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializer_class(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'next': None,
            'previous': None,
            'results': serializer.data,
        })


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
        'name', 'vendor_number', 'rating', 'hidden'  # Use annotated fields from PartnerOrganizationManager
    )

    # PMP-style filters mapping
    filters = (
        ('partner_types', 'organization__organization_type__in'),
        ('cso_types', 'organization__cso_type__in'),
        ('risk_ratings', 'rating__in'),
        ('rating', 'rating'),
        ('hidden', 'hidden'),
        ('sea_risk_rating', 'sea_risk_rating_name__in'),
        ('psea_assessment_date_before', 'psea_assessment_date__date__lte'),
        ('psea_assessment_date_after', 'psea_assessment_date__date__gte'),
        ('organization__vendor_number', 'organization__vendor_number__icontains'),
    )

    def get_queryset(self):
        qs = super().get_queryset()

        # Exclude hidden partners by default unless show_hidden is explicitly set to true
        # OR if 'hidden' filter is explicitly passed
        show_hidden = self.request.query_params.get('show_hidden', '').lower() in ['true', '1', 'yes']
        hidden_filter_passed = 'hidden' in self.request.query_params

        if not show_hidden and not hidden_filter_passed:
            qs = qs.filter(hidden=False)

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


class AgreementRssViewSet(AdminLogEntriesMixin, QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Agreement.objects.all()
    serializer_class = AgreementRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'agreement_number',
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
        ('cp_structures', 'country_programme__in'),
        ('partners', 'partner__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
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

    @transaction.atomic
    def perform_update(self, serializer):
        old_instance = Agreement.objects.get(pk=serializer.instance.pk) if serializer.instance.pk else None
        serializer.save()
        validator = RssAgreementValid(
            serializer.instance,
            old=old_instance,
            user=self.request.user,
        )
        if not validator.is_valid:
            raise ValidationError(validator.errors)
        # notify on suspension
        if serializer.instance.status == serializer.instance.SUSPENDED and old_instance and old_instance.status != serializer.instance.SUSPENDED:
            send_agreement_suspended_notification(serializer.instance, self.request.user)

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        """Retrieve change logs for this agreement.

        Returns paginated list of LogEntry records for this agreement.
        Supports standard pagination parameters: page, page_size.

        Response structure:
        {
            "count": <total_count>,
            "next": <url_to_next_page_or_null>,
            "previous": <url_to_previous_page_or_null>,
            "results": [<log_entries>]
        }
        """
        log_entries = self._get_admin_log_entries(self.get_object())
        return self._paginate_and_respond_consistently(log_entries, LogEntrySerializer)


class ProgrammeDocumentRssViewSet(AdminLogEntriesMixin, QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Intervention.objects.all()
    serializer_class = InterventionListSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        PartnerNameOrderingFilter,  # Allows ?ordering=partner_name as alias for agreement__partner__organization__name
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
        ('start', 'start__gte'),
        ('end', 'end__lte'),
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

    @transaction.atomic
    def perform_update(self, serializer):
        old_instance = Intervention.objects.get(pk=serializer.instance.pk) if serializer.instance.pk else None
        serializer.save()
        validator = RssInterventionValid(serializer.instance, old=old_instance, user=self.request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

    @action(detail=False, methods=['put'], url_path='bulk-close')
    def bulk_close(self, request, *args, **kwargs):
        serializer = BulkCloseProgrammeDocumentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)

    def _apply_fr_numbers(self, data):
        """Minimal: allow 'fr_numbers' to map to 'frs' IDs for PATCH/PUT.

        Also validates that FRs are not already assigned to other interventions.
        """
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

        # Validate that FRs are not already assigned to other interventions
        instance = getattr(self, 'instance', None) or self.get_object()
        for fr in qs:
            if fr.intervention:
                if (instance is None) or (not instance.id) or (fr.intervention.id != instance.id):
                    raise ValidationError({
                        'fr_numbers': [f"FR {fr.fr_number} is already assigned to {fr.intervention.number}"]
                    })

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

        # If after handling FR numbers and currency there is nothing left to update on the Intervention,
        # avoid running the global validator and just return the refreshed detail.
        if not payload:
            refreshed = Intervention.objects.select_related('planned_budget').get(pk=instance.pk)
            return Response(
                InterventionDetailSerializer(refreshed, context={'request': request}).data,
                status=status.HTTP_200_OK,
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

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        """Retrieve change logs for this programme document.

        Returns paginated list of LogEntry records for this programme document.
        Supports standard pagination parameters: page, page_size.

        Response structure:
        {
            "count": <total_count>,
            "next": <url_to_next_page_or_null>,
            "previous": <url_to_previous_page_or_null>,
            "results": [<log_entries>]
        }
        """
        log_entries = self._get_admin_log_entries(self.get_object())
        return self._paginate_and_respond_consistently(log_entries, LogEntrySerializer)


class EngagementRssViewSet(AdminLogEntriesMixin,
                           PermittedSerializerMixin,
                           mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
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

        # Add additional prefetching for detail views
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'staff_members',
                'active_pd',
                'authorized_officers',
                'users_notified',
                'offices',
                'sections',
            ).select_related(
                'partner__organization',
                'agreement__auditor_firm',
            )

        return queryset

    def get_object(self):
        """Override to ensure we get the proper subclass (SpotCheck, Audit, etc.) not base Engagement.

        This is crucial for serializers like StaffSpotCheckSerializer which expect fields
        that only exist on subclasses (e.g., internal_controls on SpotCheck).
        """
        obj = super().get_object()
        if hasattr(obj, 'get_subclass'):
            return obj.get_subclass()
        return obj

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

        # For retrieve and update, use the appropriate audit module serializer based on engagement type
        if self.action in ['retrieve', 'update', 'partial_update']:
            try:
                obj = self.get_object()
                if not obj:
                    return AuditSerializer
            except (AttributeError, KeyError):
                return AuditSerializer

            # Determine if it's a staff spot check (UNICEF-led)
            is_staff_spot_check = (
                obj.engagement_type == Engagement.TYPES.sc and
                obj.agreement and
                obj.agreement.auditor_firm and
                obj.agreement.auditor_firm.unicef_users_allowed
            )

            # Map engagement type to the appropriate serializer
            if is_staff_spot_check:
                return StaffSpotCheckSerializer
            elif obj.engagement_type == Engagement.TYPES.audit:
                return AuditSerializer
            elif obj.engagement_type == Engagement.TYPES.sc:
                return SpotCheckSerializer
            elif obj.engagement_type == Engagement.TYPES.ma:
                return MicroAssessmentSerializer
            elif obj.engagement_type == Engagement.TYPES.sa:
                return SpecialAuditSerializer

        return super().get_serializer_class()

    def perform_update(self, serializer):
        """Override to log changes using Django's LogEntry."""
        # Get the current state from DB before saving
        if serializer.instance.pk:
            old_instance = serializer.instance.__class__.objects.get(pk=serializer.instance.pk)
        else:
            old_instance = None

        requested_changes = extract_requested_changes(
            old_instance=old_instance,
            request_data=self.request.data,
            field_names={'total_value'},
        )

        serializer.save()

        # Refresh the instance to get the updated state
        serializer.instance.refresh_from_db()

        # Log the changes if we had an existing instance
        if old_instance:
            changed_fields = get_changed_fields(old_instance, serializer.instance)
            if requested_changes:
                # Keep actual changes, but also include specific requested fields that are not persisted.
                changed_fields = {**requested_changes, **changed_fields}
            if changed_fields:
                log_change(
                    user=self.request.user,
                    obj=serializer.instance,
                    changed_fields=changed_fields,
                )

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        engagement = self.get_object()
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()

        # Store old status for logging
        old_status = engagement.status

        serializer = EngagementChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        EngagementService.execute_action(
            engagement=engagement,
            action=action,
            send_back_comment=serializer.validated_data.get('send_back_comment'),
            cancel_comment=serializer.validated_data.get('cancel_comment'),
        )

        # Refresh to get updated status
        engagement.refresh_from_db()

        # Log the status change
        if old_status != engagement.status:
            log_change(
                user=request.user,
                obj=engagement,
                change_message=f"Status changed via RSS admin: {old_status} -> {engagement.status} (action: {action})",
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

        # Store old instance for logging
        old_instance = copy.copy(engagement)
        if old_instance.pk:
            old_instance = engagement.__class__.objects.get(pk=old_instance.pk)

        serializer = EngagementInitiationUpdateSerializer(
            instance=engagement,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Log the changes
        changed_fields = get_changed_fields(old_instance, instance)
        if changed_fields:
            log_change(
                user=request.user,
                obj=instance,
                change_message="Initiation data updated via RSS admin",
                changed_fields=changed_fields,
            )

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

        # Log the attachment changes
        attachment_ids = []
        if 'engagement_attachment' in request.data:
            attachment_ids.append(f"engagement_attachment: {request.data['engagement_attachment']}")
        if 'report_attachment' in request.data:
            attachment_ids.append(f"report_attachment: {request.data['report_attachment']}")

        if attachment_ids:
            log_change(
                user=request.user,
                obj=instance,
                change_message=f"Attachments updated via RSS admin: {', '.join(attachment_ids)}",
            )

        return Response(EngagementLightRssSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        """Retrieve change logs for this engagement.

        Returns paginated list of LogEntry records for this engagement.
        Supports standard pagination parameters: page, page_size.

        Response structure:
        {
            "count": <total_count>,
            "next": <url_to_next_page_or_null>,
            "previous": <url_to_previous_page_or_null>,
            "results": [<log_entries>]
        }
        """
        log_entries = self._get_admin_log_entries(self.get_object())
        return self._paginate_and_respond_consistently(log_entries, LogEntrySerializer)


class ActionPointRssViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    queryset = ActionPoint.objects.select_related(
        'assigned_to', 'assigned_by', 'author', 'section', 'office', 'location',
        'partner', 'partner__organization', 'intervention', 'cp_output',
        'engagement', 'psea_assessment', 'tpm_activity', 'travel_activity'
    ).prefetch_related(
        'comments',
        'comments__user',
        'comments__supporting_document'
    )
    permission_classes = (IsRssAdmin,)
    serializer_class = ActionPointRssDetailSerializer
    pagination_class = DynamicPageNumberPagination
    filter_backends = (
        OrderingFilter,
        SearchFilter,
        RelatedModuleFilter,
        DjangoFilterBackend,
    )
    search_fields = (
        'assigned_to__email', 'assigned_to__first_name', 'assigned_to__last_name',
        'assigned_by__email', 'assigned_by__first_name', 'assigned_by__last_name',
        'section__name', 'office__name', '=id', 'reference_number',
        'status', 'intervention__title', 'location__name', 'partner__organization__name', 'cp_output__name',
    )
    ordering_fields = (
        'cp_output__name', 'partner__organization__name', 'section__name', 'office__name',
        'assigned_to__first_name', 'assigned_to__last_name', 'due_date', 'status', 'pk', 'id'
    )
    filterset_fields = {
        'assigned_by': ['exact'],
        'assigned_to': ['exact'],
        'high_priority': ['exact'],
        'author': ['exact'],
        'section': ['exact', 'in'],
        'location': ['exact'],
        'office': ['exact'],
        'partner': ['exact'],
        'intervention': ['exact'],
        'cp_output': ['exact'],
        'engagement': ['exact'],
        'psea_assessment': ['exact'],
        'tpm_activity': ['exact'],
        'travel_activity': ['exact'],
        'status': ['exact', 'in'],
        'due_date': ['exact', 'lte', 'gte'],
    }

    def get_serializer_class(self):
        """Use list serializer for list action, detail serializer otherwise."""
        if self.action == 'list':
            return ActionPointRssListSerializer
        return ActionPointRssDetailSerializer

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
        return Response(ActionPointRssDetailSerializer(action_point, context={'request': request}).data, status=status.HTTP_200_OK)


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
    filterset_class = MonitoringActivityRssFilterSet
    ordering_fields = (
        'start_date', 'end_date', 'location', 'location_site', 'monitor_type', 'checklists_count', 'status'
    )
    search_fields = ('number',)

    def get_serializer_class(self):
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


class BulkUpdateMixin:
    """Mixin to enable bulk PATCH updates on a viewset.

    Matches the field monitoring BulkUpdateMixin implementation.
    Accepts a list of objects with IDs and updates them in a transaction.
    """
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        """Bulk update action. IDs are required to correctly identify instances to update."""
        if not isinstance(request.data, list):
            return Response({'error': 'Expected a list of items'}, status=status.HTTP_400_BAD_REQUEST)

        objects_to_update = self.filter_queryset(self.get_queryset()).filter(**{
            'id__in': [d['id'] for d in request.data],
        })
        data_by_id = {i.pop('id'): i for i in request.data}

        updated_objects = []

        for obj in objects_to_update:
            serializer = self.get_serializer(instance=obj, data=data_by_id[obj.id], partial=True)
            serializer.is_valid(raise_exception=True)
            updated_objects.append(serializer.save())

        return Response(self.get_serializer(instance=updated_objects, many=True).data, status=status.HTTP_200_OK)


class ActivityFindingsRssViewSet(NestedViewSetMixin,
                                 mixins.ListModelMixin,
                                 mixins.UpdateModelMixin,
                                 BulkUpdateMixin,
                                 viewsets.GenericViewSet):
    """RSS Admin viewset for activity question findings.

    Matches the structure of field monitoring data collection findings endpoint.
    Supports both single PATCH (via UpdateModelMixin) and bulk PATCH (via BulkUpdateMixin).
    """
    permission_classes = (IsRssAdmin,)
    queryset = ActivityQuestionOverallFinding.objects.select_related(
        'activity_question__question',
        'activity_question__partner',
        'activity_question__partner__organization',
        'activity_question__intervention',
        'activity_question__cp_output',
    ).prefetch_related(
        Prefetch(
            'activity_question__findings',
            Finding.objects.filter(value__isnull=False).prefetch_related(
                'started_checklist', 'started_checklist__author',
            ),
            to_attr='completed_findings'
        ),
        'activity_question__question__options',
    )
    serializer_class = ActivityQuestionOverallFindingRssSerializer
    pagination_class = None

    def get_parent_filter(self):
        """Filter to questions for this monitoring activity (matches eTools behavior)."""
        return {
            'activity_question__monitoring_activity_id': self.kwargs['monitoring_activity_pk'],
        }

    def filter_queryset(self, queryset):
        """Apply parent filter since NestedViewSetMixin requires parent chain setup."""
        queryset = super().filter_queryset(queryset)
        parent_filter = self.get_parent_filter()
        if parent_filter:
            queryset = queryset.filter(**parent_filter)
        return queryset


class ActivityOverallFindingsRssViewSet(NestedViewSetMixin,
                                        mixins.ListModelMixin,
                                        mixins.UpdateModelMixin,
                                        viewsets.GenericViewSet):
    """RSS Admin viewset for activity overall findings.

    Matches the structure of field monitoring data collection overall-findings endpoint.
    """
    permission_classes = (IsRssAdmin,)
    queryset = ActivityOverallFinding.objects.prefetch_related(
        'partner', 'cp_output', 'intervention',
        'monitoring_activity__checklists__overall_findings__attachments',
        'monitoring_activity__checklists__author',
    )
    serializer_class = ActivityOverallFindingRssSerializer
    pagination_class = None

    def get_parent_filter(self):
        """Filter to overall findings for this monitoring activity (matches eTools behavior)."""
        return {
            'monitoring_activity_id': self.kwargs['monitoring_activity_pk'],
        }

    def filter_queryset(self, queryset):
        """Apply parent filter since NestedViewSetMixin requires parent chain setup."""
        queryset = super().filter_queryset(queryset)
        parent_filter = self.get_parent_filter()
        if parent_filter:
            queryset = queryset.filter(**parent_filter)
        return queryset


class BaseRssAttachmentsViewSet(NestedViewSetMixin,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    """Base ViewSet for managing attachments in RSS Admin.

    Provides CRUD operations for attachments without permission filtering.
    Reuses audit module's attachment serializers.
    """
    permission_classes = (IsRssAdmin,)
    queryset = Attachment.objects.all()

    def get_queryset(self):
        """Limit RSS attachment operations to attachments that actually have a file.
        """
        qs = super().get_queryset()
        return qs.exclude(file__isnull=True).exclude(file='')

    def get_parent_filter(self):
        """Filter attachments by parent engagement."""
        parent = self.get_parent_object()
        if not parent:
            return {}

        if hasattr(parent, 'get_subclass'):
            parent = parent.get_subclass()

        return {
            'content_type_id': ContentType.objects.get_for_model(parent._meta.model).id,
            'object_id': parent.pk
        }

    def get_object(self, pk=None):
        """Get attachment object, filtering by parent engagement."""
        if self.request.method in ['GET', 'PATCH', 'DELETE']:
            self.queryset = self.filter_queryset(self.get_queryset())
        if pk:
            return get_object_or_404(self.queryset, **{"pk": pk})
        elif self.kwargs.get("pk"):
            return get_object_or_404(self.queryset, **{"pk": self.kwargs.get("pk")})

        return super().get_object()

    def perform_create(self, serializer):
        """Create attachment and link it to parent engagement."""
        serializer.instance = self.get_object(
            pk=serializer.validated_data.get("pk")
        )
        parent = self.get_parent_object()
        if hasattr(parent, 'get_subclass'):
            parent = parent.get_subclass()
        serializer.save(content_object=parent)

    def perform_update(self, serializer):
        """Update attachment."""
        parent = self.get_parent_object()
        if hasattr(parent, 'get_subclass'):
            parent = parent.get_subclass()
        serializer.save(content_object=parent)


class EngagementAttachmentsRssViewSet(BaseRssAttachmentsViewSet):
    """ViewSet for managing engagement attachments in RSS Admin.

    Reuses EngagementAttachmentSerializer from audit module.
    """
    serializer_class = EngagementAttachmentSerializer

    def get_view_name(self):
        return 'Related Documents'

    def get_parent_filter(self):
        """Filter for engagement-specific attachments (code='audit_engagement')."""
        filters = super().get_parent_filter()
        filters.update({'code': 'audit_engagement'})
        return filters


class ReportAttachmentsRssViewSet(BaseRssAttachmentsViewSet):
    """ViewSet for managing report attachments in RSS Admin.

    Reuses ReportAttachmentSerializer from audit module.
    """
    serializer_class = ReportAttachmentSerializer

    def get_view_name(self):
        return 'Report Attachments'

    def get_parent_filter(self):
        """Filter for report-specific attachments (code='audit_report')."""
        filters = super().get_parent_filter()
        filters.update({'code': 'audit_report'})
        return filters
