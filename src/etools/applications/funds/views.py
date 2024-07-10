from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _

from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer, JSONRenderer
from unicef_restlib.views import QueryStringFilterMixin
from unicef_vision.exceptions import VisionException

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.funds.models import (
    Donor,
    FundsCommitmentHeader,
    FundsCommitmentItem,
    FundsReservationHeader,
    FundsReservationItem,
    Grant,
)
from etools.applications.funds.serializer_exports import (
    DonorExportFlatSerializer,
    DonorExportSerializer,
    FundsCommitmentItemExportFlatSerializer,
    FundsReservationHeaderExportFlatSerializer,
    FundsReservationHeaderExportSerializer,
    FundsReservationItemExportFlatSerializer,
    FundsReservationItemExportSerializer,
    GrantExportFlatSerializer,
)
from etools.applications.funds.serializers import (
    DonorSerializer,
    FRHeaderSerializer,
    FRsSerializer,
    FundsCommitmentHeaderSerializer,
    FundsCommitmentItemSerializer,
    FundsReservationItemSerializer,
    GrantSerializer,
)
from etools.applications.funds.tasks import sync_single_delegated_fr
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PartnershipManagerPermission


class FRsView(APIView):
    """
    Returns the FRs requested with the values query param,
    The get endpoint in this view is meant to validate / validate and import FRs in order to be able to associate them
    with interventions.
    """
    permission_classes = (permissions.IsAdminUser,)

    def _post(self, request, *args, **kwargs):
        return Response(data={}, status=status.HTTP_201_CREATED)
    
    def post(self, request, *args, **kwargs):
        serializer = FRsSerializer(data=request.data)
        if serializer.is_valid():
           #frs = FR.objects.all()  # Here you should filter/query your FR objects as required
           #response_data = FRsSerializer(frs, many=True).data
           #TODO: Implement  
           return Response(data={}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, format=None):
        values = request.query_params.get("values", '').split(",")
        intervention_id = request.query_params.get("intervention", None)

        if not values[0]:
            return self.bad_request('Values are required')

        if len(values) > len(set(values)):
            return self.bad_request('You have duplicate records of the same FR, please make sure to add'
                                    ' each FR only one time')
        qs = FundsReservationHeader.objects.filter(fr_number__in=values)
        not_found = set(values) - set(qs.values_list('fr_number', flat=True))
        if not_found:
            nf = list(not_found)
            nf.sort()
            with transaction.atomic():
                for delegated_fr in nf:
                    # try to get this fr from vision
                    try:
                        sync_single_delegated_fr(request.user.profile.country.business_area_code, delegated_fr)
                    except VisionException as e:
                        return self.bad_request('The FR {} could not be found in eTools and could not be synced '
                                                'from Vision. {}'.format(delegated_fr, e))

            qs._result_cache = None

        if intervention_id:
            qs = qs.filter((Q(intervention__id=intervention_id) | Q(intervention__isnull=True)))
            not_found = set(values) - set(qs.values_list('fr_number', flat=True))
            if not_found:
                frs_not_found = FundsReservationHeader.objects.filter(fr_number__in=not_found)
                errors = ['FR #{0} is already being used by PD/SPD ref [{0.intervention}]'.format(
                    fr) for fr in frs_not_found]
                return self.bad_request(', '.join(errors))
        else:
            qs = qs.filter(intervention__isnull=True)

        if qs.count() != len(values):
            return self.bad_request('One or more of the FRs are used by another PD/SPD '
                                    'or could not be found in eTools.')

        all_frs_vendor_numbers = [fr.vendor_code for fr in qs.all()]
        if len(set(all_frs_vendor_numbers)) != 1:
            return self.bad_request('The FRs selected relate to various partners, please make sure to select '
                                    'FRs that relate to the PD/SPD Partner')

        if intervention_id is not None:
            try:
                intervention = Intervention.objects.get(pk=intervention_id)
            except Intervention.DoesNotExist:
                return self.bad_request('Intervention could not be found')
            else:
                if intervention.agreement.partner.vendor_number != all_frs_vendor_numbers[0]:
                    return self.bad_request('The vendor number of the selected implementing partner in eTools '
                                            'does not match the vendor number entered in the FR in VISION. '
                                            'Please correct the vendor number to continue.')

        serializer = FRsSerializer(qs)

        return Response(serializer.data)

    def bad_request(self, error_message):
        return Response(data={'error': _(error_message)}, status=status.HTTP_400_BAD_REQUEST)


class FundsReservationHeaderListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of FundsReservationHeaders.
    """
    serializer_class = FRHeaderSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )
    queryset = FundsReservationHeader.objects.all()
    search_terms = ('intervention__number__icontains', 'vendor_code__icontains', 'fr_number__icontains')
    filters = (
        ('partners', 'intervention__agreement__partner__pk__in'),
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return FundsReservationHeaderExportSerializer
            if query_params.get("format") == 'csv_flat':
                return FundsReservationHeaderExportFlatSerializer
        return super().get_serializer_class()


class FundsReservationItemListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of FundsReservationItems.
    """
    serializer_class = FundsReservationItemSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )
    queryset = FundsReservationItem.objects.all()
    search_terms = ('fund_reservation__intervention__number__icontains', 'fund_reservation__fr_number__icontains',
                    'fund_reservation__fr_ref_number__icontains')

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return FundsReservationItemExportSerializer
            if query_params.get("format") == 'csv_flat':
                return FundsReservationItemExportFlatSerializer
        return super().get_serializer_class()


class FundsCommitmentHeaderListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of FundsCommitmentHeaders.
    """
    serializer_class = FundsCommitmentHeaderSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )

    queryset = FundsCommitmentHeader.objects.all()
    search_terms = ('vendor_code__icontains', 'fc_number__icontains')


class FundsCommitmentItemListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of FundsCommitmentItems.
    """
    serializer_class = FundsCommitmentItemSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )
    queryset = FundsCommitmentItem.objects.all()
    search_terms = ('fund_commitment__vendor_code__icontains', 'fund_commitment__fc_number__icontains',
                    'fr_ref_number__icontains')

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv_flat':
                return FundsCommitmentItemExportFlatSerializer
        return super().get_serializer_class()


class GrantListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of Grants.
    """
    serializer_class = GrantSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )
    queryset = Grant.objects.all()
    search_terms = ('fund_commitment__vendor_code__icontains', 'fund_commitment__fc_number__icontains',
                    'fr_ref_number__icontains')

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv_flat':
                return GrantExportFlatSerializer
        return super().get_serializer_class()


class DonorListAPIView(QueryStringFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of Donors.
    """
    serializer_class = DonorSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        CSVRenderer,
        CSVFlatRenderer,
    )
    queryset = Donor.objects.all()
    search_terms = ('name__icontains', )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return DonorExportSerializer
            if query_params.get("format") == 'csv_flat':
                return DonorExportFlatSerializer
        return super().get_serializer_class()
