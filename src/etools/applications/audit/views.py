
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from etools.applications.attachments.models import Attachment
from etools.applications.action_points.conditions import ActionPointAuthorCondition, ActionPointAssignedByCondition, \
    ActionPointAssigneeCondition
from etools.applications.audit.conditions import (AuditModuleCondition, AuditStaffMemberCondition,
                                                  EngagementStaffMemberCondition,)
from etools.applications.audit.exports import (AuditDetailCSVRenderer, AuditorFirmCSVRenderer,
                                               EngagementCSVRenderer, MicroAssessmentDetailCSVRenderer,
                                               SpecialAuditDetailCSVRenderer, SpotCheckDetailCSVRenderer,)
from etools.applications.audit.filters import DisplayStatusFilter, UniqueIDOrderingFilter
from etools.applications.audit.metadata import AuditBaseMetadata, AuditPermissionBasedMetadata
from etools.applications.audit.models import (Audit, Auditor, Engagement, MicroAssessment, SpecialAudit,
                                              SpotCheck, UNICEFAuditFocalPoint, UNICEFUser, EngagementActionPoint)
from etools.applications.audit.purchase_order.models import AuditorFirm, AuditorStaffMember, PurchaseOrder
from etools.applications.audit.serializers.auditor import (AuditorFirmExportSerializer, AuditorFirmLightSerializer,
                                                           AuditorFirmSerializer, AuditorStaffMemberSerializer,
                                                           AuditUserSerializer, PurchaseOrderSerializer,)
from etools.applications.audit.serializers.engagement import (AuditSerializer, EngagementExportSerializer,
                                                              EngagementHactSerializer, EngagementListSerializer,
                                                              EngagementSerializer, MicroAssessmentSerializer,
                                                              SpecialAuditSerializer, SpotCheckSerializer,
                                                              EngagementActionPointSerializer,
                                                              EngagementAttachmentSerializer,
                                                              ReportAttachmentSerializer)
from etools.applications.audit.serializers.export import (AuditDetailCSVSerializer, AuditPDFSerializer,
                                                          MicroAssessmentDetailCSVSerializer,
                                                          MicroAssessmentPDFSerializer,
                                                          SpecialAuditDetailPDFSerializer, SpecialAuditPDFSerializer,
                                                          SpotCheckDetailCSVSerializer, SpotCheckPDFSerializer,)
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import NestedPermission, get_permission_for_targets
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin
from etools.applications.utils.common.pagination import DynamicPageNumberPagination
from etools.applications.utils.common.views import (ExportViewSetDataMixin, MultiSerializerViewSetMixin,
                                                    NestedViewSetMixin, SafeTenantViewSetMixin,)
from etools.applications.vision.adapters.purchase_order import POSynchronizer


class BaseAuditViewSet(
    SafeTenantViewSetMixin,
    ExportViewSetDataMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
):
    metadata_class = AuditBaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(AuditModuleCondition())
        return context


class AuditUsersViewSet(generics.ListAPIView):
    """
    Endpoint which will be used for searching users by email only.
    """

    permission_classes = (IsAuthenticated, )
    filter_backends = (SearchFilter, DjangoFilterBackend)
    filter_fields = ('email', 'purchase_order_auditorstaffmember__auditor_firm__unicef_users_allowed', )
    search_fields = ('email',)
    queryset = get_user_model().objects.all()
    serializer_class = AuditUserSerializer


class AuditorFirmViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = AuditPermissionBasedMetadata
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

        user_groups = self.request.user.groups.all()

        if UNICEFUser.as_group() in user_groups or UNICEFAuditFocalPoint.as_group() in user_groups:
            # no need to filter queryset
            pass
        elif Auditor.as_group() in user_groups:
            queryset = queryset.filter(staff_members__user=self.request.user)
        else:
            queryset = queryset.none()

        return queryset

    def get_permission_context(self):
        context = super(AuditorFirmViewSet, self).get_permission_context()

        if Auditor.as_group() in self.request.user.groups.all():
            context += [
                AuditStaffMemberCondition(self.request.user.purchase_order_auditorstaffmember.auditor_firm,
                                          self.request.user),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            AuditStaffMemberCondition(obj, self.request.user),
        ])
        return context

    @list_route(methods=['get'], url_path='users')
    def users(self, request, *args, **kwargs):
        return AuditUsersViewSet.as_view()(request._request, *args, **kwargs)


class PurchaseOrderViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = AuditPermissionBasedMetadata
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = (IsAuthenticated, )

    @list_route(methods=['get'], url_path='sync/(?P<order_number>[^/]+)')
    def sync(self, request, *args, **kwargs):
        """
        Fetch Purchase Order by vendor number. Load from etools.applications.vision if not found.
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
        self.check_serializer_permissions(serializer)

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
    BaseAuditViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Engagement.objects.all()
    serializer_class = EngagementSerializer
    serializer_action_classes = {
        'list': EngagementListSerializer,
    }
    metadata_class = AuditPermissionBasedMetadata

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
    filter_fields = ('agreement', 'agreement__auditor_firm', 'partner', 'engagement_type', 'joint_audit',
                     'agreement__auditor_firm__unicef_users_allowed', 'staff_members__user')

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

        user_groups = self.request.user.groups.all()

        if UNICEFUser.as_group() in user_groups or UNICEFAuditFocalPoint.as_group() in user_groups:
            # no need to filter queryset
            pass
        elif Auditor.as_group() in user_groups:
            queryset = queryset.filter(staff_members__user=self.request.user)
        else:
            queryset = queryset.none()

        queryset = queryset.prefetch_related(
            'partner', Prefetch('agreement', PurchaseOrder.objects.prefetch_related('auditor_firm'))
        )

        return queryset

    def get_permission_context(self):
        context = super(EngagementViewSet, self).get_permission_context()

        if Auditor.as_group() in self.request.user.groups.all():
            context += [
                AuditStaffMemberCondition(self.request.user.purchase_order_auditorstaffmember.auditor_firm,
                                          self.request.user),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            AuditStaffMemberCondition(obj.agreement.auditor_firm, self.request.user),
            EngagementStaffMemberCondition(obj, self.request.user),
        ])
        return context

    @list_route(methods=['get'], url_path='partners')
    def partners(self, request, *args, **kwargs):
        engagements = self.get_queryset()
        return EngagementPartnerView.as_view(engagements=engagements)(request._request, *args, **kwargs)

    @list_route(methods=['get'], url_path='hact')
    def hact(self, request, *args, **kwargs):
        if "partner" not in request.query_params:
            raise Http404

        engagements = Engagement.objects.filter(partner__pk=request.query_params["partner"],
                                                status=Engagement.FINAL).select_subclasses(
            "audit", "spotcheck", "microassessment", "specialaudit"
        )
        serializer = EngagementHactSerializer(engagements, many=True, context={"request": request})
        return Response(serializer.data)

    @detail_route(methods=['get'], url_path='pdf')
    def export_pdf(self, request, *args, **kwargs):
        obj = self.get_object()

        engagement_params = self.ENGAGEMENT_MAPPING.get(obj.engagement_type, {})
        pdf_serializer_class = engagement_params.get('pdf_serializer_class', None)
        template = engagement_params.get('pdf_template', None)

        if not pdf_serializer_class or not template:
            raise NotImplementedError

        # we use original serializer here for correct field labels
        serializer = self.get_serializer(
            instance=obj, serializer_class=engagement_params.get('serializer_class', None)
        )

        return render_to_pdf_response(
            request, template,
            context={'engagement': pdf_serializer_class(obj).data,
                     'serializer': serializer},
            filename='engagement_{}.pdf'.format(obj.unique_id),
        )


class EngagementManagementMixin(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    PermittedFSMActionMixin,
):
    def get_export_filename(self, format=None):
        return '{}.{}'.format(self.get_object().unique_id, (format or '').lower())


class MicroAssessmentViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = MicroAssessment.objects.all()
    serializer_class = MicroAssessmentSerializer
    export_serializer_class = MicroAssessmentDetailCSVSerializer
    renderer_classes = [JSONRenderer, MicroAssessmentDetailCSVRenderer]


class AuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    export_serializer_class = AuditDetailCSVSerializer
    renderer_classes = [JSONRenderer, AuditDetailCSVRenderer]


class SpotCheckViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpotCheck.objects.all()
    serializer_class = SpotCheckSerializer
    export_serializer_class = SpotCheckDetailCSVSerializer
    renderer_classes = [JSONRenderer, SpotCheckDetailCSVRenderer]


class SpecialAuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpecialAudit.objects.all()
    serializer_class = SpecialAuditSerializer
    export_serializer_class = SpecialAuditDetailPDFSerializer
    renderer_classes = [JSONRenderer, SpecialAuditDetailCSVRenderer]


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
    metadata_class = AuditPermissionBasedMetadata
    queryset = AuditorStaffMember.objects.all()
    serializer_class = AuditorStaffMemberSerializer
    permission_classes = BaseAuditViewSet.permission_classes + [NestedPermission]
    filter_backends = (OrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('user__first_name', 'user__email', 'user__last_name', )

    def perform_create(self, serializer, **kwargs):
        self.check_serializer_permissions(serializer, edit=True)

        instance = serializer.save(auditor_firm=self.get_parent_object(), **kwargs)
        instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.save()

    def get_permission_context(self):
        context = super(AuditorStaffMembersViewSet, self).get_permission_context()

        if Auditor.as_group() in self.request.user.groups.all():
            context += [
                AuditStaffMemberCondition(self.get_parent_object(), self.request.user),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            AuditStaffMemberCondition(obj.auditor_firm, self.request.user),
        ])
        return context


class EngagementActionPointViewSet(BaseAuditViewSet,
                                   PermittedFSMActionMixin,
                                   mixins.ListModelMixin,
                                   mixins.CreateModelMixin,
                                   mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   NestedViewSetMixin,
                                   viewsets.GenericViewSet):
    metadata_class = AuditPermissionBasedMetadata
    queryset = EngagementActionPoint.objects.all()
    serializer_class = EngagementActionPointSerializer

    permission_classes = BaseAuditViewSet.permission_classes + [NestedPermission]

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
        ])
        return context

    def perform_create(self, serializer):
        engagement = self.get_parent_object()
        serializer.save(engagement=engagement, partner_id=engagement.partner_id)


class BaseAuditAttachmentsViewSet(BaseAuditViewSet,
                                  mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  NestedViewSetMixin,
                                  viewsets.GenericViewSet):
    metadata_class = AuditPermissionBasedMetadata
    queryset = Attachment.objects.all()

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'content_type_id': ContentType.objects.get_for_model(parent.get_subclass()._meta.model).id,
            'object_id': parent.pk
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object().get_subclass())


class EngagementAttachmentsViewSet(BaseAuditAttachmentsViewSet):
    serializer_class = EngagementAttachmentSerializer
    permission_classes = BaseAuditViewSet.permission_classes + [
        get_permission_for_targets('audit.engagement.engagement_attachments')
    ]

    def get_view_name(self):
        return _('Related Documents')

    def get_parent_filter(self):
        filters = super(EngagementAttachmentsViewSet, self).get_parent_filter()
        filters.update({'code': 'audit_engagement'})
        return filters


class ReportAttachmentsViewSet(BaseAuditAttachmentsViewSet):
    serializer_class = ReportAttachmentSerializer
    permission_classes = BaseAuditViewSet.permission_classes + [
        get_permission_for_targets('audit.engagement.report_attachments')
    ]

    def get_view_name(self):
        return _('Report Attachments')

    def get_parent_filter(self):
        filters = super(ReportAttachmentsViewSet, self).get_parent_filter()
        filters.update({'code': 'audit_report'})
        return filters
