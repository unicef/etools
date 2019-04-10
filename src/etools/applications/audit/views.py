from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.http import Http404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from unicef_attachments.models import Attachment, AttachmentLink
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.audit.conditions import (
    AuditModuleCondition,
    AuditStaffMemberCondition,
    EngagementStaffMemberCondition,
)
from etools.applications.audit.exports import (
    AuditDetailCSVRenderer,
    AuditorFirmCSVRenderer,
    EngagementCSVRenderer,
    MicroAssessmentDetailCSVRenderer,
    SpecialAuditDetailCSVRenderer,
    SpotCheckDetailCSVRenderer,
)
from etools.applications.audit.filters import DisplayStatusFilter, EngagementFilter, UniqueIDOrderingFilter
from etools.applications.audit.models import (
    Audit,
    Auditor,
    Engagement,
    EngagementActionPoint,
    MicroAssessment,
    SpecialAudit,
    SpotCheck,
    UNICEFAuditFocalPoint,
    UNICEFUser,
)
from etools.applications.audit.purchase_order.models import AuditorFirm, AuditorStaffMember, PurchaseOrder
from etools.applications.audit.purchase_order.synchronizers import POSynchronizer
from etools.applications.audit.serializers.attachments import (
    AuditAttachmentLinkSerializer,
    EngagementAttachmentLinkSerializer,
    ListAttachmentLinkSerializer,
    MicroAssessmentAttachmentLinkSerializer,
    SpecialAuditAttachmentLinkSerializer,
    SpotCheckAttachmentLinkSerializer,
)
from etools.applications.audit.serializers.auditor import (
    AuditorFirmExportSerializer,
    AuditorFirmLightSerializer,
    AuditorFirmSerializer,
    AuditorStaffMemberSerializer,
    AuditUserSerializer,
    PurchaseOrderSerializer,
)
from etools.applications.audit.serializers.engagement import (
    AuditSerializer,
    EngagementActionPointSerializer,
    EngagementAttachmentSerializer,
    EngagementExportSerializer,
    EngagementHactSerializer,
    EngagementListSerializer,
    EngagementSerializer,
    MicroAssessmentSerializer,
    ReportAttachmentSerializer,
    SpecialAuditSerializer,
    SpotCheckSerializer,
    StaffSpotCheckListSerializer,
    StaffSpotCheckSerializer,
)
from etools.applications.audit.serializers.export import (
    AuditDetailCSVSerializer,
    AuditPDFSerializer,
    MicroAssessmentDetailCSVSerializer,
    MicroAssessmentPDFSerializer,
    SpecialAuditDetailCSVSerializer,
    SpecialAuditPDFSerializer,
    SpotCheckDetailCSVSerializer,
    SpotCheckPDFSerializer,
)
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import get_permission_for_targets, NestedPermission
from etools.applications.permissions2.metadata import BaseMetadata, PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin


class BaseAuditViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
):
    metadata_class = BaseMetadata
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
    metadata_class = PermissionBasedMetadata
    queryset = AuditorFirm.objects.filter(hidden=False)
    serializer_class = AuditorFirmSerializer
    serializer_action_classes = {
        'list': AuditorFirmLightSerializer
    }
    renderer_classes = [JSONRenderer, AuditorFirmCSVRenderer]
    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('name', 'email')
    ordering_fields = ('name', )
    filter_fields = ('country', 'unicef_users_allowed')

    def get_queryset(self):
        queryset = super().get_queryset()

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
        context = super().get_permission_context()

        if Auditor.as_group() in self.request.user.groups.all() and \
           hasattr(self.request.user, 'purchase_order_auditorstaffmember'):
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

    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request, *args, **kwargs):
        return AuditUsersViewSet.as_view()(request._request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='current_tenant')
    def current_tenant(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            pk__in=Engagement.objects.values_list('agreement__auditor_firm', flat=True))
        serializer = AuditorFirmExportSerializer(queryset, many=True)
        return Response(serializer.data)


class PurchaseOrderViewSet(
    BaseAuditViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (DjangoFilterBackend, )
    filter_fields = ('auditor_firm__unicef_users_allowed', )

    @action(detail=False, methods=['get'], url_path='sync/(?P<order_number>[^/]+)')
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
        queryset = super().get_queryset()

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
    unicef_engagements = False
    serializer_class = EngagementSerializer
    serializer_action_classes = {
        'list': EngagementListSerializer,
    }
    metadata_class = PermissionBasedMetadata

    renderer_classes = [JSONRenderer, EngagementCSVRenderer]

    filter_backends = (
        SearchFilter, DisplayStatusFilter, DjangoFilterBackend,
        UniqueIDOrderingFilter, OrderingFilter,
    )
    search_fields = ('partner__name', 'agreement__auditor_firm__name')
    ordering_fields = ('agreement__order_number', 'agreement__auditor_firm__name',
                       'partner__name', 'engagement_type', 'status')
    filter_class = EngagementFilter
    export_filename = 'engagements'

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

        return serializer_class or super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()

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

        if self.action in ['list', 'export_list_csv']:
            queryset = queryset.filter(agreement__auditor_firm__unicef_users_allowed=self.unicef_engagements)

        return queryset

    def get_permission_context(self):
        context = super().get_permission_context()

        if Auditor.as_group() in self.request.user.groups.all() and \
           hasattr(self.request.user, 'purchase_order_auditorstaffmember'):
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

    @action(detail=False, methods=['get'], url_path='partners')
    def partners(self, request, *args, **kwargs):
        engagements = self.get_queryset()
        return EngagementPartnerView.as_view(engagements=engagements)(request._request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='hact')
    def hact(self, request, *args, **kwargs):
        if "partner" not in request.query_params:
            raise Http404

        engagements = Engagement.objects.filter(partner__pk=request.query_params["partner"],
                                                status=Engagement.FINAL).select_subclasses(
            "audit", "spotcheck", "microassessment", "specialaudit"
        )
        serializer = EngagementHactSerializer(engagements, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='pdf')
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

    @action(detail=False, methods=['get'], url_path='csv', renderer_classes=[EngagementCSVRenderer])
    def export_list_csv(self, request, *args, **kwargs):
        engagements = self.filter_queryset(self.get_queryset())
        serializer = EngagementExportSerializer(engagements, many=True)

        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(self.export_filename, timezone.now().date())
        })


class EngagementManagementMixin(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    PermittedFSMActionMixin,
):
    csv_export_serializer = EngagementExportSerializer

    @action(detail=True, methods=['get'], url_path='csv', renderer_classes=[EngagementCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        engagement = self.get_object()
        serializer = self.csv_export_serializer(engagement)

        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}.csv'.format(engagement.unique_id)
        })


class MicroAssessmentViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = MicroAssessment.objects.all()
    serializer_class = MicroAssessmentSerializer
    csv_export_serializer = MicroAssessmentDetailCSVSerializer

    @action(detail=True, methods=['get'], url_path='csv', renderer_classes=[MicroAssessmentDetailCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        return super().export_csv(request, *args, **kwargs)


class AuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    csv_export_serializer = AuditDetailCSVSerializer

    @action(detail=True, methods=['get'], url_path='csv', renderer_classes=[AuditDetailCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        return super().export_csv(request, *args, **kwargs)


class SpotCheckViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpotCheck.objects.all()
    serializer_class = SpotCheckSerializer
    csv_export_serializer = SpotCheckDetailCSVSerializer

    @action(detail=True, methods=['get'], url_path='csv', renderer_classes=[SpotCheckDetailCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        return super().export_csv(request, *args, **kwargs)


class StaffSpotCheckViewSet(SpotCheckViewSet):
    unicef_engagements = True
    export_filename = 'staff_spot_checks'
    serializer_class = StaffSpotCheckSerializer
    serializer_action_classes = {
        'list': StaffSpotCheckListSerializer
    }


class SpecialAuditViewSet(EngagementManagementMixin, EngagementViewSet):
    queryset = SpecialAudit.objects.all()
    serializer_class = SpecialAuditSerializer
    csv_export_serializer = SpecialAuditDetailCSVSerializer

    @action(detail=True, methods=['get'], url_path='csv', renderer_classes=[SpecialAuditDetailCSVRenderer])
    def export_csv(self, request, *args, **kwargs):
        return super().export_csv(request, *args, **kwargs)


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
    metadata_class = PermissionBasedMetadata
    queryset = AuditorStaffMember.objects.all()
    serializer_class = AuditorStaffMemberSerializer
    permission_classes = BaseAuditViewSet.permission_classes + [NestedPermission]
    filter_backends = (OrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('user__first_name', 'user__email', 'user__last_name', )
    filter_fields = ('user__profile__country__schema_name', 'user__profile__country__name',
                     'user__profile__countries_available__schema_name', 'user__profile__countries_available__name')

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset = queryset.filter(hidden=False)

        return queryset

    def perform_create(self, serializer, **kwargs):
        self.check_serializer_permissions(serializer, edit=True)

        instance = serializer.save(auditor_firm=self.get_parent_object(), **kwargs)
        if not instance.user.profile.country:
            instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.countries_available.add(self.request.user.profile.country)
        instance.user.groups.add(Auditor.as_group())
        instance.user.profile.save()

    def perform_update(self, serializer):
        self.check_serializer_permissions(serializer, edit=True)

        super().perform_update(serializer)
        instance = serializer.save(auditor_firm=self.get_parent_object())
        if not instance.user.profile.country:
            instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.countries_available.add(self.request.user.profile.country)
        instance.user.profile.save()

    def perform_destroy(self, instance):
        # deactivate staff member & user
        instance.hidden = True
        instance.save()
        if not instance.user.is_unicef_user():
            instance.user.is_active = False
            instance.user.save()

    def get_permission_context(self):
        context = super().get_permission_context()

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
                                   mixins.ListModelMixin,
                                   mixins.CreateModelMixin,
                                   mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   NestedViewSetMixin,
                                   viewsets.GenericViewSet):
    metadata_class = PermissionBasedMetadata
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
        serializer.save(engagement=engagement)


class BaseAuditAttachmentsViewSet(BaseAuditViewSet,
                                  mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  NestedViewSetMixin,
                                  viewsets.GenericViewSet):
    metadata_class = PermissionBasedMetadata
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
        filters = super().get_parent_filter()
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
        filters = super().get_parent_filter()
        filters.update({'code': 'audit_report'})
        return filters


class BaseAttachmentLinksView(generics.ListCreateAPIView):
    metadata_class = PermissionBasedMetadata
    permission_classes = [IsAuthenticated]

    def get_content_type(self, model_name):
        try:
            return ContentType.objects.get_by_natural_key(
                "audit",
                model_name,
            )
        except ContentType.DoesNotExist:
            raise NotFound()

    def set_content_object(self):
        self.content_type = self.get_content_type(self.content_model_name)

        try:
            self.object_id = self.kwargs.get("object_pk")
            model_cls = self.content_type.model_class()
            self.content_object = model_cls.objects.get(
                pk=self.object_id
            )
        except model_cls.DoesNotExist:
            raise NotFound()

    def get_serializer_context(self):
        self.set_content_object()
        context = super().get_serializer_context()
        context["content_type"] = self.content_type
        context["object_id"] = self.object_id
        return context

    def get_queryset(self):
        self.set_content_object()
        return AttachmentLink.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = ListAttachmentLinkSerializer(queryset, many=True)
        return Response(serializer.data)


class EngagementAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = EngagementAttachmentLinkSerializer
    content_model_name = "engagement"


class SpotCheckAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = SpotCheckAttachmentLinkSerializer
    content_model_name = "spotcheck"


class MicroAssessmentAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = MicroAssessmentAttachmentLinkSerializer
    content_model_name = "microassessment"


class AuditAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = AuditAttachmentLinkSerializer
    content_model_name = "audit"


class SpecialAuditAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = SpecialAuditAttachmentLinkSerializer
    content_model_name = "specialaudit"
