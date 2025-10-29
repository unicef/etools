import copy

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.audit.models import Engagement
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.partners.filters import InterventionEditableByFilter, ShowAmendmentsFilter
from etools.applications.partners.models import Agreement, Intervention, InterventionBudget, PartnerOrganization
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
)
from etools.applications.partners.tasks import send_pd_to_vision
from etools.applications.partners.utils import send_agreement_suspended_notification
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import (
    AgreementRssSerializer,
    BulkCloseProgrammeDocumentsSerializer,
    EngagementChangeStatusSerializer,
    EngagementAttachmentsUpdateSerializer,
    EngagementInitiationUpdateSerializer,
    EngagementLightRssSerializer,
    PartnerOrganizationRssSerializer,
)
from etools.applications.rss_admin.validation import RssAgreementValid, RssInterventionValid
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.fields import CURRENCY_LIST
from etools.libraries.djangolib.views import FilterQueryMixin


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
        serializer = self.get_serializer(instance=instance, data=payload, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class EngagementRssViewSet(viewsets.GenericViewSet):
    queryset = Engagement.objects.all()
    serializer_class = EngagementLightRssSerializer
    permission_classes = (IsRssAdmin,)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        engagement = self.get_object()
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()
        serializer = EngagementChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        # Execute FSM actions; permissions are enforced by the transition decorators
        if action == EngagementChangeStatusSerializer.ACTION_SUBMIT:
            engagement.submit()
        elif action == EngagementChangeStatusSerializer.ACTION_SEND_BACK:
            engagement.send_back(serializer.validated_data['send_back_comment'])
        elif action == EngagementChangeStatusSerializer.ACTION_CANCEL:
            engagement.cancel(serializer.validated_data['cancel_comment'])
        elif action == EngagementChangeStatusSerializer.ACTION_FINALIZE:
            engagement.finalize()

        engagement.save()
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
