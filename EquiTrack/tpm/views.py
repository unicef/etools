from django.db.models import Prefetch

from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter, OrderingFilter, DjangoFilterBackend

from partners.models import Agreement, Intervention, InterventionResultLink
from reports.models import Result
from tpm.models import TPMLocation, TPMPartner, TPMVisit, TPMVisitReport, TPMActivity, \
                       TPMLowResult, TPMSectorCovered, ThirdPartyMonitor, TPMPermission, \
                       UNICEFFocalPoint
from utils.common.views import MultiSerializerViewSetMixin, FSMTransitionActionMixin
from utils.common.pagination import DynamicPageNumberPagination
from tpm.serializers.partner import TPMPartnerLightSerializer, TPMPartnerSerializer
from tpm.serializers.attachments import TPMAttachmentsSerializer
from tpm.serializers.visit import TPMVisitLightSerializer, TPMVisitSerializer, \
                                  TPMReportSerializer
from tpm.view_mixins import TPMMetadataClassMixin


class TPMPartnerViewSet(
    TPMMetadataClassMixin,
    MultiSerializerViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    # todo: allow access only for self organization if parner
    queryset = TPMPartner.objects.filter(hidden=False)
    serializer_class = TPMPartnerSerializer
    serializer_action_classes = {
        'list': TPMPartnerLightSerializer
    }
    filter_backends = (SearchFilter, OrderingFilter, DjangoFilterBackend)
    search_fields = ('vendor_number', 'name')
    ordering_fields = ('vendor_number', 'name', 'country')
    filter_fields = ('status', )


class TPMVisitViewSet(
    TPMMetadataClassMixin,
    MultiSerializerViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    FSMTransitionActionMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = TPMVisit.objects.all().prefetch_related(
        'tpm_partner',
        'tpm_activities',
        'tpm_activities__unicef_focal_point',
        'tpm_activities__partnership',
        'tpm_activities__tpm_sectors',
        'tpm_activities__tpm_sectors__sector',
        'tpm_activities__tpm_sectors__tpm_low_results',
        'tpm_activities__tpm_sectors__tpm_low_results__result',
        'tpm_activities__tpm_sectors__tpm_low_results__tpm_locations',
        'tpm_report',
        'attachments',
    )
    serializer_class = TPMVisitSerializer
    pagination_class = DynamicPageNumberPagination
    serializer_action_classes = {
        'list': TPMVisitLightSerializer
    }

    def get_queryset(self):
        queryset = super(TPMVisitViewSet, self).get_queryset()

        user_type = TPMPermission._get_user_type(self.request.user)
        if not user_type:
            return queryset.none()
        if user_type == ThirdPartyMonitor:
            queryset = queryset.filter(
                tpm_partner=self.request.user.tpm_tpmpartnerstaffmember.tpm_partner
            )
        return queryset
