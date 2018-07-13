from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.action_points.conditions import ActionPointAuthorCondition, ActionPointAssignedByCondition, \
    ActionPointAssigneeCondition
from etools.applications.attachments.models import Attachment
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import NestedPermission, get_permission_for_targets
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin
from etools.applications.reports.models import Result, Sector
from etools.applications.reports.serializers.v1 import ResultLightSerializer, SectionSerializer

from etools.applications.tpm.conditions import (
    TPMModuleCondition, TPMStaffMemberCondition, TPMVisitTPMFocalPointCondition, TPMVisitUNICEFFocalPointCondition,)
from etools.applications.tpm.export.renderers import (
    TPMActionPointCSVRenderer, TPMActionPointFullCSVRenderer, TPMActivityCSVRenderer, TPMLocationCSVRenderer,
    TPMPartnerContactsCSVRenderer, TPMPartnerCSVRenderer, TPMVisitCSVRenderer,)
from etools.applications.tpm.export.serializers import (
    TPMActionPointExportSerializer, TPMActionPointFullExportSerializer, TPMActivityExportSerializer,
    TPMLocationExportSerializer, TPMPartnerContactsSerializer, TPMPartnerExportSerializer, TPMVisitExportSerializer,)
from etools.applications.tpm.filters import ReferenceNumberOrderingFilter
from etools.applications.tpm.metadata import TPMBaseMetadata, TPMPermissionBasedMetadata
from etools.applications.tpm.models import PME, ThirdPartyMonitor, TPMActionPoint, TPMActivity, TPMVisit, UNICEFUser
from etools.applications.tpm.serializers.attachments import TPMPartnerAttachmentsSerializer, \
    TPMVisitReportAttachmentsSerializer, ActivityAttachmentsSerializer, ActivityReportSerializer
from etools.applications.tpm.serializers.partner import (
    TPMPartnerLightSerializer, TPMPartnerSerializer, TPMPartnerStaffMemberSerializer,)
from etools.applications.tpm.serializers.visit import (
    TPMActionPointSerializer, TPMVisitDraftSerializer, TPMVisitLightSerializer, TPMVisitSerializer)

from etools.applications.tpm.tpmpartners.models import TPMPartner, TPMPartnerStaffMember
from etools.applications.utils.common.pagination import DynamicPageNumberPagination
from etools.applications.utils.common.views import (
    MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin,)
from etools.applications.vision.adapters.tpm_adapter import TPMPartnerManualSynchronizer


class BaseTPMViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
):
    metadata_class = TPMBaseMetadata
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
    metadata_class = TPMPermissionBasedMetadata
    queryset = TPMPartner.objects.all()
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
        queryset = super(TPMPartnerViewSet, self).get_queryset()

        if getattr(self, 'action', None) == 'list':
            queryset = queryset.country_partners()

        user_groups = self.request.user.groups.all()

        if UNICEFUser.as_group() in user_groups or PME.as_group() in user_groups:
            # no need to filter queryset
            pass
        elif ThirdPartyMonitor.as_group() in user_groups:
            queryset = queryset.filter(staff_members__user=self.request.user)
        else:
            queryset = queryset.none()

        return queryset

    def get_permission_context(self):
        context = super(TPMPartnerViewSet, self).get_permission_context()

        if ThirdPartyMonitor.as_group() in self.request.user.groups.all() and \
           hasattr(self.request.user, 'tpmpartners_tpmpartnerstaffmember'):
            context += [
                TPMStaffMemberCondition(
                    self.request.user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                    self.request.user
                ),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            TPMStaffMemberCondition(obj, self.request.user),
        ])
        return context

    @list_route(methods=['get'], url_path='sync/(?P<vendor_number>[^/]+)')
    def sync(self, request, *args, **kwargs):
        """
        Fetch TPM Partner by vendor number. Load from etools.applications.vision if not found.
        """
        queryset = self.filter_queryset(self.get_queryset())
        instance = queryset.filter(vendor_number=kwargs.get('vendor_number')).first()

        if not instance:
            handler = TPMPartnerManualSynchronizer(
                country=request.user.profile.country,
                object_number=kwargs.get('vendor_number')
            )
            handler.sync()
            instance = queryset.filter(vendor_number=kwargs.get('vendor_number')).first()

        if not instance:
            raise Http404

        self.check_object_permissions(self.request, instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @detail_route(methods=['post'], url_path='activate')
    def activate(self, request, *args, **kwargs):
        tpm_partner = self.get_object()
        tpm_partner.activate(request.user.profile.country)

        return Response(TPMPartnerSerializer(instance=tpm_partner).data)

    @list_route(methods=['get'], url_path='export', renderer_classes=(TPMPartnerCSVRenderer,))
    def export(self, request, *args, **kwargs):
        tpm_partners = TPMPartner.objects.all().order_by('vendor_number')
        serializer = TPMPartnerExportSerializer(tpm_partners, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_vendors_{}.csv'.format(timezone.now().date())
        })


class TPMStaffMembersViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    NestedViewSetMixin,
    viewsets.GenericViewSet
):
    metadata_class = TPMPermissionBasedMetadata
    queryset = TPMPartnerStaffMember.objects.all()
    serializer_class = TPMPartnerStaffMemberSerializer
    permission_classes = BaseTPMViewSet.permission_classes + [NestedPermission]

    filter_backends = (OrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('user__first_name', 'user__email', 'user__last_name', )
    filter_fields = ('user__is_active', )

    def perform_create(self, serializer, **kwargs):
        self.check_serializer_permissions(serializer, edit=True)

        instance = serializer.save(tpm_partner=self.get_parent_object(), **kwargs)
        instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.save()

    @list_route(methods=['get'], url_path='export', renderer_classes=(TPMPartnerContactsCSVRenderer,))
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
        queryset = super(ImplementingPartnerView, self).get_queryset()

        if self.visits is not None:
            queryset = queryset.filter(activity__in=self.visits.values_list(
                'tpm_activities__id', flat=True)).distinct()

        return queryset


class VisitsSectionView(generics.ListAPIView):
    queryset = Sector.objects.all()
    serializer_class = SectionSerializer
    permission_classes = (IsAuthenticated,)

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    visits = None

    def get_queryset(self):
        queryset = super(VisitsSectionView, self).get_queryset()

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
        queryset = super(VisitsCPOutputView, self).get_queryset()

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
    metadata_class = TPMPermissionBasedMetadata
    queryset = TPMVisit.objects.all().prefetch_related(
        'tpm_partner',
        'tpm_activities__unicef_focal_points',
    )
    serializer_class = TPMVisitSerializer
    serializer_action_classes = {
        'create': TPMVisitDraftSerializer,
        'list': TPMVisitLightSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter, DjangoFilterBackend, )
    search_fields = (
        'tpm_partner__name', 'tpm_activities__partner__name',
        'tpm_activities__locations__name', 'tpm_activities__locations__p_code',
    )
    ordering_fields = (
        'tpm_partner__name', 'status'
    )
    filter_fields = (
        'tpm_partner', 'tpm_activities__section', 'tpm_activities__partner', 'tpm_activities__locations',
        'tpm_activities__cp_output', 'tpm_activities__intervention', 'tpm_activities__date', 'status',
        'tpm_activities__unicef_focal_points', 'tpm_partner_focal_points',
    )

    def get_queryset(self):
        queryset = super(TPMVisitViewSet, self).get_queryset()

        user_groups = self.request.user.groups.all()

        if UNICEFUser.as_group() in user_groups or PME.as_group() in user_groups:
            # no need to filter queryset
            pass
        elif ThirdPartyMonitor.as_group() in user_groups and \
                hasattr(self.request.user, 'tpmpartners_tpmpartnerstaffmember'):
            queryset = queryset.filter(
                tpm_partner=self.request.user.tpmpartners_tpmpartnerstaffmember.tpm_partner
            ).exclude(status=TPMVisit.STATUSES.draft)
        else:
            queryset = queryset.none()

        return queryset

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update'] and \
                'pk' in self.kwargs and \
                self.get_object().status == TPMVisit.STATUSES.draft:
            return TPMVisitDraftSerializer
        return super(TPMVisitViewSet, self).get_serializer_class()

    @list_route(methods=['get'], url_path='activities/implementing-partners')
    def implementing_partners(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return ImplementingPartnerView.as_view(visits=visits)(request, *args, **kwargs)

    @list_route(methods=['get'], url_path='activities/sections')
    def sections(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return VisitsSectionView.as_view(visits=visits)(request, *args, **kwargs)

    @list_route(methods=['get'], url_path='activities/cp-outputs')
    def cp_outputs(self, request, *args, **kwargs):
        visits = self.get_queryset()
        return VisitsCPOutputView.as_view(visits=visits)(request, *args, **kwargs)

    @list_route(methods=['get'], url_path='export', renderer_classes=(TPMVisitCSVRenderer,))
    def visits_export(self, request, *args, **kwargs):
        tpm_visits = self.get_queryset().prefetch_related(
            'tpm_activities', 'tpm_activities__section', 'tpm_activities__partner',
            'tpm_activities__intervention', 'tpm_activities__locations', 'tpm_activities__unicef_focal_points',
            'tpm_partner_focal_points'
        ).order_by('id')
        serializer = TPMVisitExportSerializer(tpm_visits, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_visits_{}.csv'.format(timezone.now().date())
        })

    def get_permission_context(self):
        context = super(TPMVisitViewSet, self).get_permission_context()

        if ThirdPartyMonitor.as_group() in self.request.user.groups.all() and \
           hasattr(self.request.user, 'tpmpartners_tpmpartnerstaffmember'):
            context += [
                TPMStaffMemberCondition(
                    self.request.user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                    self.request.user
                ),
            ]

        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            TPMStaffMemberCondition(obj.tpm_partner, self.request.user),
            TPMVisitUNICEFFocalPointCondition(obj, self.request.user),
            TPMVisitTPMFocalPointCondition(obj, self.request.user),
        ])
        return context

    @list_route(methods=['get'], url_path='activities/export', renderer_classes=(TPMActivityCSVRenderer,))
    def activities_export(self, request, *args, **kwargs):
        tpm_activities = TPMActivity.objects.filter(
            tpm_visit__in=self.get_queryset(),
        ).prefetch_related(
            'tpm_visit', 'section', 'locations', 'cp_output'
        ).order_by('tpm_visit', 'id')
        serializer = TPMActivityExportSerializer(tpm_activities, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_tasks_{}.csv'.format(timezone.now().date())
        })

    @list_route(methods=['get'], url_path='locations/export', renderer_classes=(TPMLocationCSVRenderer,))
    def locations_export(self, request, *args, **kwargs):
        tpm_locations = TPMActivity.locations.through.objects.filter(
            activity__in=self.get_queryset().values_list('tpm_activities__id', flat=True),
        ).prefetch_related(
            'activity', 'location', 'activity__tpmactivity__tpm_visit', 'activity__tpmactivity__section',
            'activity__cp_output'
        ).order_by('activity__tpmactivity__tpm_visit', 'activity', 'id')
        serializer = TPMLocationExportSerializer(tpm_locations, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_locations_{}.csv'.format(timezone.now().date())
        })

    @list_route(methods=['get'], url_path='action-points/export', renderer_classes=(TPMActionPointFullCSVRenderer,))
    def action_points_export(self, request, *args, **kwargs):
        action_points = TPMActionPoint.objects.filter(tpm_activity__tpm_visit__in=self.get_queryset()).order_by('id')

        serializer = TPMActionPointFullExportSerializer(action_points, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_action_points_{}.csv'.format(timezone.now().date())
        })

    @detail_route(methods=['get'])
    def export_pdf(self, request, *args, **kwargs):
        return render_to_pdf_response(request, "tpm/activities_list_pdf.html", context={
            "activities": self.get_object().tpm_activities.all(),
        })

    @detail_route(methods=['get'], url_path='visit-letter')
    def tpm_visit_letter(self, request, *args, **kwargs):
        visit = self.get_object()
        return render_to_pdf_response(
            request, "tpm/visit_letter_pdf.html", context={
                "visit": visit
            },
            filename="visit_letter_{}.pdf".format(visit.reference_number)
        )


class TPMActionPointViewSet(BaseTPMViewSet,
                            PermittedFSMActionMixin,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            NestedViewSetMixin,
                            viewsets.GenericViewSet):
    metadata_class = TPMPermissionBasedMetadata
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

    @list_route(methods=['get'], url_path='export', renderer_classes=(TPMActionPointCSVRenderer,))
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
    metadata_class = TPMPermissionBasedMetadata
    queryset = Attachment.objects.all()


class PartnerAttachmentsViewSet(BaseTPMAttachmentsViewSet):
    serializer_class = TPMPartnerAttachmentsSerializer

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
        return _('Related Documents')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
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
        return _('Related Documents')

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
