from functools import cache

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Exists, OuterRef, Q
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_attachments.models import Attachment, AttachmentLink
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import get_permission_for_targets, NestedPermission
from etools.applications.permissions2.metadata import BaseMetadata, PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin
from etools.applications.reports.models import Result, Section
from etools.applications.reports.serializers.v1 import ResultLightSerializer, SectionSerializer
from etools.applications.tpm.conditions import (
    TPMModuleCondition,
    TPMStaffMemberCondition,
    TPMVisitTPMFocalPointCondition,
    TPMVisitUNICEFFocalPointCondition,
)
from etools.applications.tpm.export.renderers import (
    TPMActionPointCSVRenderer,
    TPMActionPointFullCSVRenderer,
    TPMActivityCSVRenderer,
    TPMLocationCSVRenderer,
    TPMPartnerContactsCSVRenderer,
    TPMPartnerCSVRenderer,
    TPMVisitCSVRenderer,
)
from etools.applications.tpm.export.serializers import (
    TPMActionPointExportSerializer,
    TPMActionPointFullExportSerializer,
    TPMActivityExportSerializer,
    TPMLocationExportSerializer,
    TPMPartnerContactsSerializer,
    TPMPartnerExportSerializer,
    TPMVisitExportSerializer,
)
from etools.applications.tpm.filters import (
    ReferenceNumberOrderingFilter,
    StaffMembersOrderingFilter,
    TPMActivityFilter,
    TPMStaffMembersFilterSet,
    TPMVisitFilter,
)
from etools.applications.tpm.models import PME, ThirdPartyMonitor, TPMActionPoint, TPMActivity, TPMVisit, UNICEFUser
from etools.applications.tpm.serializers.attachments import (
    ActivityAttachmentsSerializer,
    ActivityReportSerializer,
    TPMActivityAttachmentLinkSerializer,
    TPMAttachmentLinkSerializer,
    TPMPartnerAttachmentsSerializer,
    TPMVisitAttachmentLinkSerializer,
    TPMVisitAttachmentsSerializer,
    TPMVisitReportAttachmentsSerializer,
)
from etools.applications.tpm.serializers.partner import (
    TPMPartnerLightSerializer,
    TPMPartnerSerializer,
    TPMPartnerStaffMemberRealmSerializer,
)
from etools.applications.tpm.serializers.visit import (
    TPMActionPointSerializer,
    TPMActivityLightSerializer,
    TPMVisitDraftSerializer,
    TPMVisitLightSerializer,
    TPMVisitSerializer,
)
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.tpm.tpmpartners.synchronizers import TPMPartnerSynchronizer
from etools.applications.users.mixins import TPM_ACTIVE_GROUPS
from etools.applications.users.models import Realm


class BaseTPMViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
):
    metadata_class = BaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(TPMModuleCondition())
        return context


class TPMPartnerViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    PermittedFSMActionMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = TPMPartner.objects.all().select_related('organization')
    serializer_class = TPMPartnerSerializer
    serializer_action_classes = {
        'list': TPMPartnerLightSerializer
    }
    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('vendor_number', 'name')
    ordering_fields = ('vendor_number', 'name', 'phone_number', 'email')
    filter_fields = (
        'blocked', 'hidden', 'deleted_flag',
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if getattr(self, 'action', None) == 'list':
            queryset = queryset.country_partners()
        user_groups = self.request.user.groups.values_list('name', flat=True)

        if UNICEFUser.name in user_groups or PME.name in user_groups:
            # no need to filter queryset
            pass
        elif ThirdPartyMonitor.name in user_groups:
            queryset = queryset.filter(organization=self.request.user.profile.organization)
        else:
            queryset = queryset.none()

        return queryset

    def get_permission_context(self):
        context = super().get_permission_context()

        if ThirdPartyMonitor.as_group() in self.request.user.groups.all():
            context += [
                TPMStaffMemberCondition(self.request.user.profile.organization, self.request.user),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            TPMStaffMemberCondition(obj.organization, self.request.user),
        ])
        return context

    @action(detail=False, methods=['get'], url_path='sync/(?P<vendor_number>[^/]+)')
    def sync(self, request, *args, **kwargs):
        """
        Fetch TPM Partner by vendor number. Load from etools.applications.vision if not found.
        """
        queryset = self.filter_queryset(self.get_queryset())
        instance = queryset.filter(organization__vendor_number=kwargs.get('vendor_number')).first()

        if not instance:
            handler = TPMPartnerSynchronizer(vendor=kwargs.get('vendor_number'))
            handler.sync()
            instance = queryset.filter(organization__vendor_number=kwargs.get('vendor_number')).first()

        if not instance:
            raise Http404

        self.check_object_permissions(self.request, instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, *args, **kwargs):
        tpm_partner = self.get_object()
        tpm_partner.activate(request.user.profile.country)

        return Response(TPMPartnerSerializer(instance=tpm_partner).data)

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=(TPMPartnerCSVRenderer,))
    def export(self, request, *args, **kwargs):

        tpm_partners = self.filter_queryset(self.get_queryset()).order_by('organization__vendor_number')

        serializer = TPMPartnerExportSerializer(tpm_partners, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_vendors_{}.csv'.format(timezone.now().date())
        })


class TPMStaffMembersViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    NestedViewSetMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = get_user_model().objects.select_related(None).select_related('profile')
    serializer_class = TPMPartnerStaffMemberRealmSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpmpartners.tpmpartner.staff_members')
    ]

    filter_backends = (StaffMembersOrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('first_name', 'email', 'last_name', )
    filterset_class = TPMStaffMembersFilterSet

    def get_queryset(self):
        queryset = super().get_queryset()
        context_realms_qs = Realm.objects.filter(
            organization=self.get_parent_object().organization,
            country=connection.tenant,
            group__name__in=TPM_ACTIVE_GROUPS
        )
        queryset = queryset\
            .annotate(has_realm=Exists(context_realms_qs.filter(user=OuterRef('pk'))))\
            .annotate(has_active_realm=Exists(context_realms_qs.filter(user=OuterRef('pk'), is_active=True)))\
            .filter(has_realm=True)\
            .distinct()
        return queryset

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {'realms__organization': parent.organization}

    @cache
    def get_parent_object(self):
        return super().get_parent_object()

    def get_permission_context(self):
        context = super().get_permission_context()

        parent = self.get_parent_object()
        if parent:
            context += [
                TPMStaffMemberCondition(parent.organization, self.request.user),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            TPMStaffMemberCondition(obj.profile.organization, self.request.user),
        ])
        return context

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=(TPMPartnerContactsCSVRenderer,))
    def export(self, request, *args, **kwargs):
        partner = self.get_parent_object()
        queryset = self.filter_queryset(self.get_queryset())
        serializer = TPMPartnerContactsSerializer(queryset, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_#{}_contacts_{}.csv'.format(
                partner.vendor_number, timezone.now().date()
            ),
        })


class ImplementingPartnerView(generics.ListAPIView):
    queryset = PartnerOrganization.objects.filter(hidden=False)
    serializer_class = MinimalPartnerOrganizationListSerializer
    permission_classes = (IsAuthenticated,)

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    visits = None

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.visits is not None:
            queryset = queryset.filter(activity__in=self.visits.values_list(
                'tpm_activities__id', flat=True)).distinct()

        return queryset


class VisitsSectionView(generics.ListAPIView):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = (IsAuthenticated,)

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    visits = None

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.visits is not None:
            queryset = queryset.filter(tpm_activities__tpm_visit__in=self.visits).distinct()

        return queryset


class VisitsCPOutputView(generics.ListAPIView):
    queryset = Result.objects.filter(hidden=False)
    serializer_class = ResultLightSerializer
    permission_classes = (IsAuthenticated,)

    filter_backends = (SearchFilter,)
    search_fields = ('name', 'code', 'result_type__name')

    visits = None

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.visits is not None:
            queryset = queryset.filter(activity__in=self.visits.values_list(
                'tpm_activities__id', flat=True)).distinct()

        return queryset


class TPMVisitViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    PermittedFSMActionMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = TPMVisit.objects.select_related('tpm_partner').prefetch_related(
        'tpm_activities__unicef_focal_points',
    )
    serializer_class = TPMVisitSerializer
    serializer_action_classes = {
        'create': TPMVisitDraftSerializer,
        'list': TPMVisitLightSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter, DjangoFilterBackend, )
    search_fields = (
        'tpm_partner__organization__name', 'tpm_activities__partner__organization__name',
        'tpm_activities__locations__name', 'tpm_activities__locations__p_code',
    )
    ordering_fields = (
        'tpm_partner__name', 'status'
    )
    filterset_class = TPMVisitFilter

    def get_queryset(self):
        queryset = super().get_queryset().distinct()

        user_groups = self.request.user.groups.all()

        if UNICEFUser.as_group() in user_groups or PME.as_group() in user_groups:
            # no need to filter queryset
            pass
        elif ThirdPartyMonitor.as_group() in user_groups and \
                hasattr(self.request.user.profile.organization, 'tpmpartner'):
            queryset = queryset.filter(
                tpm_partner=self.request.user.profile.organization.tpmpartner
            ).exclude(
                Q(status=TPMVisit.STATUSES.draft) |
                Q(status=TPMVisit.STATUSES.cancelled, date_of_assigned__isnull=True)  # cancelled draft
            )
        else:
            queryset = queryset.none()

        return queryset

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update'] and \
                'pk' in self.kwargs and \
                self.get_object().status == TPMVisit.STATUSES.draft:
            return TPMVisitDraftSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'], url_path='activities/implementing-partners')
    def implementing_partners(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return ImplementingPartnerView.as_view(visits=visits)(request._request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='activities/sections')
    def sections(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return VisitsSectionView.as_view(visits=visits)(request._request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='activities/cp-outputs')
    def cp_outputs(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return VisitsCPOutputView.as_view(visits=visits)(request._request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=(TPMVisitCSVRenderer,))
    def visits_export(self, request, *args, **kwargs):
        tpm_visits = self.filter_queryset(self.get_queryset().prefetch_related(
            'tpm_activities', 'tpm_activities__section', 'tpm_activities__partner',
            'tpm_activities__intervention', 'tpm_activities__locations', 'tpm_activities__unicef_focal_points',
            'tpm_partner_focal_points'
        ).order_by('id'))
        serializer = TPMVisitExportSerializer(tpm_visits, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_visits_{}.csv'.format(timezone.now().date())
        })

    def get_permission_context(self):
        context = super().get_permission_context()

        if ThirdPartyMonitor.as_group() in self.request.user.groups:
            context.append(TPMStaffMemberCondition(self.request.user.profile.organization, self.request.user))

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            TPMStaffMemberCondition(obj.tpm_partner.organization, self.request.user),
            TPMVisitUNICEFFocalPointCondition(obj, self.request.user),
            TPMVisitTPMFocalPointCondition(obj, self.request.user),
        ])
        return context

    @action(detail=False, methods=['get'], url_path='activities/export', renderer_classes=(TPMActivityCSVRenderer,))
    def activities_export(self, request, *args, **kwargs):
        tpm_activities = TPMActivity.objects.filter(
            tpm_visit__in=self.filter_queryset(self.get_queryset()),
        ).prefetch_related(
            'tpm_visit', 'section', 'locations', 'cp_output'
        ).order_by('tpm_visit', 'id')
        serializer = TPMActivityExportSerializer(tpm_activities, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_tasks_{}.csv'.format(timezone.now().date())
        })

    @action(detail=False, methods=['get'], url_path='locations/export', renderer_classes=(TPMLocationCSVRenderer,))
    def locations_export(self, request, *args, **kwargs):
        tpm_locations = TPMActivity.locations.through.objects.filter(
            activity__in=self.filter_queryset(self.get_queryset()).values_list('tpm_activities__id', flat=True),
        ).prefetch_related(
            'activity', 'location', 'activity__tpmactivity__tpm_visit', 'activity__tpmactivity__section',
            'activity__cp_output'
        ).order_by('activity__tpmactivity__tpm_visit', 'activity', 'id')
        serializer = TPMLocationExportSerializer(tpm_locations, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_locations_{}.csv'.format(timezone.now().date())
        })

    @action(detail=False, methods=['get'], url_path='action-points/export', renderer_classes=(TPMActionPointFullCSVRenderer,))
    def action_points_export(self, request, *args, **kwargs):
        action_points = TPMActionPoint.objects.filter(tpm_activity__tpm_visit__in=self.get_queryset()).order_by('id')

        serializer = TPMActionPointFullExportSerializer(action_points, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_action_points_{}.csv'.format(timezone.now().date())
        })

    @action(detail=True, methods=['get'])
    def export_pdf(self, request, *args, **kwargs):
        return render_to_pdf_response(request, "tpm/activities_list_pdf.html", context={
            "activities": self.get_object().tpm_activities.all(),
        })

    @action(detail=True, methods=['get'], url_path='visit-letter')
    def tpm_visit_letter(self, request, *args, **kwargs):
        visit = self.get_object()
        return render_to_pdf_response(
            request, "tpm/visit_letter_pdf.html", context={
                "visit": visit
            },
            filename="visit_letter_{}.pdf".format(visit.reference_number)
        )


class TPMActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TPMActivity.objects.all()
    serializer_class = TPMActivityLightSerializer
    filterset_class = TPMActivityFilter

    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('tpm_visit__tpm_partner__vendor_number', 'tpm_visit__tpm_partner__name',
                     'partner__organization__name', 'partner__vendor_number')


class TPMActionPointViewSet(BaseTPMViewSet,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            NestedViewSetMixin,
                            viewsets.GenericViewSet):
    metadata_class = PermissionBasedMetadata
    queryset = TPMActionPoint.objects.all()
    serializer_class = TPMActionPointSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [NestedPermission]

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
        ])
        return context

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=(TPMActionPointCSVRenderer,))
    def csv_export(self, request, *args, **kwargs):
        serializer = TPMActionPointExportSerializer(self.filter_queryset(self.get_queryset()), many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_action_points_{}.csv'.format(
                self.get_root_object().reference_number, timezone.now().date()
            )
        })


class BaseTPMAttachmentsViewSet(BaseTPMViewSet,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                NestedViewSetMixin,
                                viewsets.GenericViewSet):
    metadata_class = PermissionBasedMetadata
    queryset = Attachment.objects.all()


class PartnerAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = TPMPartnerAttachmentsSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpmpartners.tpmpartner.attachments')
    ]

    def get_view_name(self):
        return _('Attachments')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'content_type_id': ContentType.objects.get_for_model(TPMPartner).id,
            'object_id': parent.pk,
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object())


class VisitReportAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = TPMVisitReportAttachmentsSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpm.tpmvisit.report_attachments')
    ]

    def get_view_name(self):
        return _('Overall Report')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'code': 'visit_report_attachments',
            'content_type_id': ContentType.objects.get_for_model(TPMVisit).id,
            'object_id': parent.pk,
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object())


class VisitAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = TPMVisitAttachmentsSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpm.tpmvisit.attachments')
    ]

    def get_view_name(self):
        return _('Related Documents for Overall Visit')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'code': 'visit_attachments',
            'content_type_id': ContentType.objects.get_for_model(TPMVisit).id,
            'object_id': parent.pk,
        }

    def perform_create(self, serializer):
        serializer.save(content_object=self.get_parent_object())


class ActivityAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = ActivityAttachmentsSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpm.tpmactivity.attachments')
    ]

    def get_view_name(self):
        return _('Related Documents by Task')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'code': 'activity_attachments',
            'content_type_id': ContentType.objects.get_for_model(TPMActivity).id,
            'object_id__in': parent.tpm_activities.values_list('id', flat=True),
        }

    def perform_create(self, serializer):
        serializer.save(content_type=ContentType.objects.get_for_model(TPMActivity))


class ActivityReportAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = ActivityReportSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [
        get_permission_for_targets('tpm.tpmactivity.report_attachments')
    ]

    def get_view_name(self):
        return _('Reports by Task')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'code': 'activity_report',
            'content_type_id': ContentType.objects.get_for_model(TPMActivity).id,
            'object_id__in': parent.tpm_activities.values_list('id', flat=True),
        }

    def perform_create(self, serializer):
        serializer.save(content_type=ContentType.objects.get_for_model(TPMActivity))


class BaseAttachmentLinksView(generics.ListCreateAPIView):
    metadata_class = PermissionBasedMetadata
    permission_classes = [IsAuthenticated]

    def get_content_type(self, model_name):
        try:
            return ContentType.objects.get_by_natural_key(
                "tpm",
                model_name,
            )
        except ContentType.DoesNotExist:
            raise NotFound()

    def get_serializer_context(self):
        self.set_content_object()
        context = super().get_serializer_context()
        context["content_type"] = self.content_type
        context["object_id"] = self.object_id
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = TPMAttachmentLinkSerializer(queryset, many=True)
        return Response(serializer.data)


class ActivityAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = TPMActivityAttachmentLinkSerializer

    def set_content_object(self):
        self.content_type = self.get_content_type("tpmactivity")

        try:
            self.object_id = self.kwargs.get("object_pk")
            model_cls = self.content_type.model_class()
            self.content_object = model_cls.objects.get(
                pk=self.object_id
            )
        except model_cls.DoesNotExist:
            raise NotFound()

    def get_queryset(self):
        self.set_content_object()
        return AttachmentLink.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
        )


class VisitAttachmentLinksView(BaseAttachmentLinksView):
    serializer_class = TPMVisitAttachmentLinkSerializer

    def set_content_object(self):
        self.content_type = self.get_content_type("tpmvisit")
        self.activity_content_type = self.get_content_type("tpmactivity")
        try:
            self.object_id = self.kwargs.get("object_pk")
            model_cls = self.content_type.model_class()
            self.content_object = model_cls.objects.get(
                pk=self.object_id
            )
        except model_cls.DoesNotExist:
            raise NotFound()

    def get_queryset(self):
        self.set_content_object()
        object_id_list = TPMActivity.objects.values_list("id", flat=True).filter(tpm_visit=self.object_id)
        return AttachmentLink.objects.filter(
            content_type=self.activity_content_type,
            object_id__in=object_id_list,
        )
