from django.http import Http404
from django.utils import timezone
from easy_pdf.rendering import render_to_pdf_response

from rest_framework import generics, viewsets, mixins
from rest_framework.decorators import list_route, detail_route
from rest_framework.filters import SearchFilter, OrderingFilter, DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from partners.models import PartnerOrganization
from partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from reports.models import Result
from reports.serializers.v1 import ResultLightSerializer
from users.models import Section
from users.serializers import SectionSerializer
from utils.common.views import MultiSerializerViewSetMixin, FSMTransitionActionMixin, \
    NestedViewSetMixin, SafeTenantViewSetMixin
from utils.common.pagination import DynamicPageNumberPagination
from vision.adapters.tpm_adapter import TPMPartnerManualSynchronizer
from .filters import ReferenceNumberOrderingFilter
from .metadata import TPMBaseMetadata, TPMPermissionBasedMetadata
from .models import TPMPartner, TPMVisit, ThirdPartyMonitor, TPMPermission, TPMPartnerStaffMember, TPMActivity
from .serializers.partner import TPMPartnerLightSerializer, TPMPartnerSerializer, TPMPartnerStaffMemberSerializer
from .serializers.visit import TPMVisitLightSerializer, TPMVisitSerializer, TPMVisitDraftSerializer
from .permissions import IsPMEorReadonlyPermission
from .export.renderers import TPMActivityCSVRenderer, TPMLocationCSVRenderer, TPMPartnerCSVRenderer
from .export.serializers import TPMActivityExportSerializer, TPMLocationExportSerializer, TPMPartnerExportSerializer


class BaseTPMViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = TPMBaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = (IsAuthenticated, )


class TPMPartnerViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    FSMTransitionActionMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = TPMPermissionBasedMetadata
    queryset = TPMPartner.objects.all()
    serializer_class = TPMPartnerSerializer
    serializer_action_classes = {
        'list': TPMPartnerLightSerializer
    }
    permission_classes = (IsAuthenticated, IsPMEorReadonlyPermission,)
    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('vendor_number', 'name', 'phone_number', 'email')
    ordering_fields = ('vendor_number', 'name', 'phone_number', 'email')
    filter_fields = (
        'status', 'blocked', 'hidden', 'deleted_flag',
    )

    def get_queryset(self):
        queryset = super(TPMPartnerViewSet, self).get_queryset()

        user_type = TPMPermission._get_user_type(self.request.user)
        if not user_type or user_type == ThirdPartyMonitor:
            queryset = queryset.filter(staff_members__user=self.request.user)

        return queryset

    @list_route(methods=['get'], url_path='sync/(?P<vendor_number>[^/]+)')
    def sync(self, request, *args, **kwargs):
        """
        Fetch TPM Partner by vendor number. Load from vision if not found.
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
    queryset = TPMPartnerStaffMember.objects.all()
    serializer_class = TPMPartnerStaffMemberSerializer
    permission_classes = (IsAuthenticated, IsPMEorReadonlyPermission, )
    filter_backends = (OrderingFilter, SearchFilter, DjangoFilterBackend, )
    ordering_fields = ('user__email', 'user__first_name', 'id', )
    search_fields = ('user__first_name', 'user__email', 'user__last_name', )

    def perform_create(self, serializer, **kwargs):
        instance = serializer.save(tpm_partner=self.get_parent_object(), **kwargs)
        instance.user.profile.country = self.request.user.profile.country
        instance.user.profile.save()


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
            queryset = queryset.filter(tpmactivity__tpm_visit__in=self.visits).distinct()

        return queryset


class VisitsSectionView(generics.ListAPIView):
    queryset = Section.objects.all()
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
            queryset = queryset.filter(tpmactivity__tpm_visit__in=self.visits).distinct()

        return queryset


class TPMVisitViewSet(
    BaseTPMViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    FSMTransitionActionMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = TPMPermissionBasedMetadata
    queryset = TPMVisit.objects.all().prefetch_related(
        'tpm_partner',
        'unicef_focal_points',
    )
    serializer_class = TPMVisitSerializer
    serializer_action_classes = {
        'create': TPMVisitDraftSerializer,
        'list': TPMVisitLightSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter, DjangoFilterBackend, )
    search_fields = (
        'tpm_partner__name', 'tpm_activities__implementing_partner__name'
    )
    ordering_fields = (
        'tpm_partner__name', 'status'
    )
    filter_fields = (
        'tpm_partner', 'tpm_activities__section', 'tpm_activities__implementing_partner', 'tpm_activities__locations',
        'tpm_activities__cp_output', 'tpm_activities__partnership', 'tpm_activities__date', 'status',
        'unicef_focal_points', 'tpm_partner_focal_points',
    )

    def get_queryset(self):
        queryset = super(TPMVisitViewSet, self).get_queryset()

        user_type = TPMPermission._get_user_type(self.request.user)
        if not user_type:
            return queryset.none()
        if user_type == ThirdPartyMonitor:
            queryset = queryset.filter(
                tpm_partner=self.request.user.tpm_tpmpartnerstaffmember.tpm_partner,
            ).exclude(status=TPMVisit.STATUSES.draft)
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

    @list_route(methods=['get'], url_path='activities/export', renderer_classes=(TPMActivityCSVRenderer,))
    def activities_export(self, request, *args, **kwargs):
        tpm_activities = TPMActivity.objects.filter(
            tpm_visit__in=self.get_queryset(),
        ).prefetch_related(
            'tpm_visit', 'section', 'locations', 'cp_output'
        ).order_by('tpm_visit', 'id')
        serializer = TPMActivityExportSerializer(tpm_activities, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_attachments_{}.csv'.format(timezone.now().date())
        })

    @list_route(methods=['get'], url_path='locations/export', renderer_classes=(TPMLocationCSVRenderer,))
    def locations_export(self, request, *args, **kwargs):
        tpm_locations = TPMActivity.locations.through.objects.filter(
            tpmactivity__tpm_visit__in=self.get_queryset(),
        ).prefetch_related(
            'tpmactivity', 'location', 'tpmactivity__tpm_visit', 'tpmactivity__section', 'tpmactivity__cp_output'
        ).order_by('tpmactivity__tpm_visit', 'tpmactivity', 'id')
        serializer = TPMLocationExportSerializer(tpm_locations, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=tpm_locations_{}.csv'.format(timezone.now().date())
        })

    @detail_route(methods=['get'])
    def export_pdf(self, request, *args, **kwargs):
        return render_to_pdf_response(request, "tpm/activities_list_pdf.html", context={
            "activities": self.get_object().tpm_activities.all(),
        })

    @detail_route(methods=['get'], url_path='visit-letter')
    def tpm_visit_letter(self, request, *args, **kwargs):
        return render_to_pdf_response(request, "tpm/visit_letter_pdf.html", context={
            "visit": self.get_object(),
        })
