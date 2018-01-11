from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models import Prefetch
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import list_route, detail_route
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from audit.exports import AuditorFirmCSVRenderer, EngagementCSVRenderer
from audit.filters import DisplayStatusFilter, UniqueIDOrderingFilter
from audit.metadata import AuditBaseMetadata, EngagementMetadata
from audit.models import (
    Engagement, MicroAssessment, Audit, SpotCheck, Auditor, AuditPermission, SpecialAudit, UNICEFUser)
from audit.purchase_order.models import AuditorFirm, AuditorStaffMember, PurchaseOrder
from audit.permissions import HasCreatePermission, CanCreateStaffMembers
from audit.serializers.auditor import (
    AuditorFirmExportSerializer, AuditorFirmLightSerializer, AuditorFirmSerializer, AuditorStaffMemberSerializer,
    PurchaseOrderSerializer,)
from audit.serializers.engagement import (
    AuditSerializer, EngagementExportSerializer, EngagementLightSerializer, EngagementSerializer,
    MicroAssessmentSerializer, SpecialAuditSerializer, SpotCheckSerializer,)
from audit.serializers.export import (
    AuditPDFSerializer, MicroAssessmentPDFSerializer, SpecialAuditPDFSerializer, SpotCheckPDFSerializer,)
from partners.models import PartnerOrganization
from partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from utils.common.views import (
    ExportViewSetDataMixin, FSMTransitionActionMixin, MultiSerializerViewSetMixin, NestedViewSetMixin,
    SafeTenantViewSetMixin,)
from utils.common.pagination import DynamicPageNumberPagination
from vision.adapters.purchase_order import POSynchronizer


class BaseAuditViewSet(
    SafeTenantViewSetMixin,
    ExportViewSetDataMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = AuditBaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = (IsAuthenticated, )


class AuditorFirmViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = AuditorFirm.objects.filter(hidden=False)
    serializer_class = AuditorFirmSerializer
    serializer_action_classes = {
        'list': AuditorFirmLightSerializer
    }
    export_serializer_class = AuditorFirmExportSerializer
    renderer_classes = [JSONRenderer, AuditorFirmCSVRenderer]
    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('name', 'email')
    ordering_fields = ('name', )
    filter_fields = ('country', )

    def get_queryset(self):
        queryset = super(AuditorFirmViewSet, self).get_queryset()

        user_type = AuditPermission._get_user_type(self.request.user)
        if not user_type or user_type == Auditor:
            queryset = queryset.filter(staff_members__user=self.request.user)

        return queryset


class PurchaseOrderViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    @list_route(methods=['get'], url_path='sync/(?P<order_number>[^/]+)')
    def sync(self, request, *args, **kwargs):
        """
        Fetch Purchase Order by vendor number. Load from vision if not found.
        """
        queryset = self.filter_queryset(self.get_queryset())
        instance = queryset.filter(order_number=kwargs.get('order_number')).first()

        if not instance:
            handler = POSynchronizer(
                country=request.user.profile.country,
                object_number=kwargs.get('order_number')
            )
            handler.sync()
            instance = queryset.filter(order_number=kwargs.get('order_number')).first()

        if not instance:
            raise Http404

        self.check_object_permissions(self.request, instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class EngagementPartnerView(generics.ListAPIView):
    queryset = PartnerOrganization.objects.filter(hidden=False)
    serializer_class = MinimalPartnerOrganizationListSerializer
    permission_classes = (IsAuthenticated, )

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    engagements = None

    def get_queryset(self):
        queryset = super(EngagementPartnerView, self).get_queryset()

        if self.engagements is not None:
            queryset = queryset.filter(engagement__in=self.engagements).distinct()

        return queryset


class EngagementViewSet(
    mixins.CreateModelMixin,
    BaseAuditViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Engagement.objects.all()
    serializer_class = EngagementSerializer
    serializer_action_classes = {
        'list': EngagementLightSerializer
    }
    metadata_class = EngagementMetadata

    permission_classes = (IsAuthenticated, HasCreatePermission,)
    export_serializer_class = EngagementExportSerializer
    export_filename = 'engagements'
    renderer_classes = [JSONRenderer, EngagementCSVRenderer]

    filter_backends = (
        SearchFilter, DisplayStatusFilter, DjangoFilterBackend,
        UniqueIDOrderingFilter, OrderingFilter,
    )
    search_fields = ('partner__name', 'agreement__auditor_firm__name')
    ordering_fields = ('agreement__order_number', 'agreement__auditor_firm__name',
                       'partner__name', 'engagement_type', 'status')
    filter_fields = ('agreement', 'agreement__auditor_firm', 'partner', 'engagement_type')

    ENGAGEMENT_MAPPING = {
        Engagement.TYPES.audit: {
            'serializer_class': AuditSerializer,
            'pdf_serializer_class': AuditPDFSerializer,
            'pdf_template': 'audit/audit_pdf.html',
        },
        Engagement.TYPES.ma: {
            'serializer_class': MicroAssessmentSerializer,
            'pdf_serializer_class': MicroAssessmentPDFSerializer,
            'pdf_template': 'audit/microassessment_pdf.html',
        },
        Engagement.TYPES.sa: {
            'serializer_class': SpecialAuditSerializer,
            'pdf_serializer_class': SpecialAuditPDFSerializer,
            'pdf_template': 'audit/special_audit_pdf.html',
        },
        Engagement.TYPES.sc: {
            'serializer_class': SpotCheckSerializer,
            'pdf_serializer_class': SpotCheckPDFSerializer,
            'pdf_template': 'audit/spotcheck_pdf.html',
        },
    }

    def get_serializer_class(self):
        serializer_class = None

        if self.action == 'create':
            engagement_type = self.request.data.get('engagement_type', None)
            serializer_class = self.ENGAGEMENT_MAPPING.get(engagement_type, {}).get('serializer_class', None)

        return serializer_class or super(EngagementViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = super(EngagementViewSet, self).get_queryset()

        queryset = queryset.prefetch_related(
            'partner', Prefetch('agreement', PurchaseOrder.objects.prefetch_related('auditor_firm'))
        )

        user_type = AuditPermission._get_user_type(self.request.user)
        if not user_type or user_type == Auditor:
            queryset = queryset.filter(staff_members__user=self.request.user)

        if user_type == UNICEFUser:
            queryset = queryset.exclude(engagement_type=Engagement.TYPES.sa)

        return queryset

    @list_route(methods=['get'], url_path='partners')
    def partners(self, request, *args, **kwargs):
        engagements = self.get_queryset()
        return EngagementPartnerView.as_view(engagements=engagements)(request, *args, **kwargs)

    @detail_route(methods=['get'], url_path='pdf')
    def export_pdf(self, request, *args, **kwargs):
        obj = self.get_object()

        if not AuditPermission.objects.filter(instance=obj, user=request.user).exists():
            self.permission_denied(
                request, message=_('You have no access to this engagement.')
            )

        engagement_params = self.ENGAGEMENT_MAPPING.get(obj.engagement_type, {})
        serializer_class = engagement_params.get('pdf_serializer_class', None)
        template = engagement_params.get('pdf_template', None)

        if not serializer_class or not template:
            raise NotImplementedError

        return render_to_pdf_response(
            request, template,
            context={'engagement': serializer_class(obj).data},
            filename='engagement_{}.pdf'.format(obj.unique_id),
        )


class EngagementManagementMixin(
    FSMTransitionActionMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin
):
    pass


class MicroAssessmentViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = MicroAssessment.objects.all()
    serializer_class = MicroAssessmentSerializer


class AuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer


class SpotCheckViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpotCheck.objects.all()
    serializer_class = SpotCheckSerializer


class SpecialAuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpecialAudit.objects.all()
    serializer_class = SpecialAuditSerializer


class AuditorStaffMembersViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    NestedViewSetMixin,
    viewsets.GenericViewSet
):
    queryset = AuditorStaffMember.objects.all()
    serializer_class = AuditorStaffMemberSerializer
    permission_classes = (IsAuthenticated, CanCreateStaffMembers, )
    filter_backends = (OrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('user__first_name', 'user__email', 'user__last_name', )

    def perform_create(self, serializer, **kwargs):
        instance = serializer.save(auditor_firm=self.get_parent_object(), **kwargs)
        instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.save()
