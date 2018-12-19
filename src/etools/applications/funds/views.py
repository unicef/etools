import functools
import operator

from django.db.models import Q
from django.utils.translation import ugettext as _

from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer, JSONRenderer

from etools.applications.EquiTrack.mixins import ExportModelMixin
from etools.applications.EquiTrack.renderers import CSVFlatRenderer
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
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PartnershipManagerPermission


class FRsView(APIView):
    """
    Returns the FRs requested with the values query param
    """
    permission_classes = (permissions.IsAdminUser,)

    def filter_by_donors(self, qs, donor_pks):
        grant_numbers = Grant.objects.values_list(
            "name",
            flat=True
        ).filter(donor__pk__in=donor_pks)
        qs = self.filter_by_grants(qs, None, list(grant_numbers))
        return qs

    def filter_by_grants(self, qs, grant_pks, grant_numbers=[]):
        """Filter queryset by grant ids provided

        `name` field in Grants table matches `grant_number` in
        FundsReservationItem, from FundsReservationItem we can
        access FundsReservationHeader
        """
        if not isinstance(grant_numbers, list):
            return qs.none()

        if grant_pks:
            grant_qs = Grant.objects.values_list(
                "name",
                flat=True
            ).filter(pk__in=grant_pks)
            if grant_numbers:
                grant_qs = grant_qs.filter(name__in=grant_numbers)
            grant_numbers = grant_qs

        if not grant_numbers:
            qs = qs.none()
        else:
            fr_headers = FundsReservationItem.objects.values_list(
                "fund_reservation__pk",
                flat=True
            ).filter(grant_number__in=grant_numbers)
            qs = qs.filter(pk__in=fr_headers)
        return qs

    def get(self, request, format=None):
        values = request.query_params.get("values", '').split(",")
        intervention_id = request.query_params.get("intervention", None)

        if not values[0]:
            return self.bad_request('Values are required')

        qs = FundsReservationHeader.objects.filter(fr_number__in=values)

        not_found = set(values) - set(qs.values_list('fr_number', flat=True))
        if not_found:
            nf = list(not_found)
            nf.sort()
            return self.bad_request('The FR {} could not be found on eTools'.format(', '.join(nf)))

        if intervention_id:
            qs = qs.filter((Q(intervention__id=intervention_id) | Q(intervention__isnull=True)))
            not_found = set(values) - set(qs.values_list('fr_number', flat=True))
            if not_found:
                frs_not_found = FundsReservationHeader.objects.filter(fr_number__in=not_found)
                errors = ['FR #{0} is already being used by PD/SSFA ref [{0.intervention}]'.format(
                    fr) for fr in frs_not_found]
                return self.bad_request(', '.join(errors))
        else:
            qs = qs.filter(intervention__isnull=True)

        donors = [x for x in request.query_params.get("donors", "").split(",") if x]
        if donors:
            qs = self.filter_by_donors(qs, donors)

        grants = [x for x in request.query_params.get("grants", "").split(",") if x]
        if grants:
            qs = self.filter_by_grants(qs, grants)

        if not grants and not donors and qs.count() != len(values):
            return self.bad_request('One or more of the FRs are used by another PD/SSFA '
                                    'or could not be found in eTools.')

        all_frs_vendor_numbers = [fr.vendor_code for fr in qs.all()]
        if len(set(all_frs_vendor_numbers)) != 1:
            return self.bad_request('The FRs selected relate to various partners, please make sure to select '
                                    'FRs that relate to the PD/SSFA Partner')

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


class FundsReservationHeaderListAPIView(ExportModelMixin, ListAPIView):
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

    def get_queryset(self, format=None):
        q = FundsReservationHeader.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(vendor_code__icontains=query_params.get("search")) |
                    Q(fr_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class FundsReservationItemListAPIView(ExportModelMixin, ListAPIView):
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

    def get_queryset(self, format=None):
        q = FundsReservationItem.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(fund_reservation__intervention__number__icontains=query_params.get("search")) |
                    Q(fund_reservation__fr_number__icontains=query_params.get("search")) |
                    Q(fund_reservation__fr_ref_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class FundsCommitmentHeaderListAPIView(ExportModelMixin, ListAPIView):
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

    def get_queryset(self, format=None):
        q = FundsCommitmentHeader.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(vendor_code__icontains=query_params.get("search")) |
                    Q(fc_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class FundsCommitmentItemListAPIView(ExportModelMixin, ListAPIView):
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

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv_flat':
                return FundsCommitmentItemExportFlatSerializer
        return super().get_serializer_class()

    def get_queryset(self, format=None):
        q = FundsCommitmentItem.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(fund_commitment__vendor_code__icontains=query_params.get("search")) |
                    Q(fund_commitment__fc_number__icontains=query_params.get("search")) |
                    Q(fr_ref_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class GrantListAPIView(ExportModelMixin, ListAPIView):
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

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv_flat':
                return GrantExportFlatSerializer
        return super().get_serializer_class()

    def get_queryset(self, format=None):
        q = Grant.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(fund_commitment__vendor_code__icontains=query_params.get("search")) |
                    Q(fund_commitment__fc_number__icontains=query_params.get("search")) |
                    Q(fr_ref_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class DonorListAPIView(ExportModelMixin, ListAPIView):
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

    def get_queryset(self, format=None):
        q = Donor.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(name__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q
