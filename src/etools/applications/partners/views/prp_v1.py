from datetime import timedelta

from django.db.models import CharField, Count, OuterRef, Q, Subquery, Sum
from django.utils.timezone import now

from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.funds.models import FundsReservationHeader
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.partners.permissions import ListCreateAPIMixedPermission, ReadOnlyAPIUser
from etools.applications.partners.serializers.prp_v1 import (
    InterventionPDFileSerializer,
    PRPInterventionListSerializer,
    PRPPartnerOrganizationListSerializer,
)
from etools.applications.partners.views.helpers import set_tenant_or_fail
from etools.libraries.djangolib.models import MaxDistinct


class PRPPDFileView(APIView):
    permission_classes = (ReadOnlyAPIUser,)

    def get(self, request, intervention_pk):

        workspace = request.query_params.get('workspace', None)
        set_tenant_or_fail(workspace)

        intervention = get_object_or_404(Intervention, pk=intervention_pk)

        return Response(InterventionPDFileSerializer(intervention).data)


class PRPInterventionPagination(LimitOffsetPagination):
    default_limit = 100


class PRPPartnerPagination(LimitOffsetPagination):
    default_limit = 300


class PRPInterventionListAPIView(QueryStringFilterMixin, ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    filter_backends = (PartnerScopeFilter,)
    pagination_class = PRPInterventionPagination

    frs_query = FundsReservationHeader.objects.filter(
        intervention=OuterRef("pk")
    ).order_by().values("intervention")

    queryset = (Intervention.objects.filter(
        Q(status=Intervention.DRAFT, date_sent_to_partner__isnull=False) | ~Q(status=Intervention.DRAFT),
        result_links__ll_results__applied_indicators__isnull=False,
        reporting_requirements__isnull=False,
        in_amendment=False
    ).exclude(
        Q(status__in=[Intervention.ENDED,
                      Intervention.CANCELLED,
                      Intervention.CLOSED,
                      Intervention.TERMINATED,
                      Intervention.EXPIRED]) & Q(modified__lt=now() - timedelta(days=365))
    ).prefetch_related(
        'result_links__cp_output',
        'result_links__ll_results',
        'result_links__ll_results__applied_indicators__indicator',
        'result_links__ll_results__applied_indicators__disaggregation__disaggregation_values',
        'special_reporting_requirements',
        'reporting_requirements',
        'frs',
        'partner_focal_points',
        'unicef_focal_points',
        'agreement__authorized_officers',
        'agreement__partner',
        'amendments',
        'flat_locations',
        'sections'
    ).annotate(
        frs__actual_amt_local__sum=Subquery(
            frs_query.annotate(total=Sum("actual_amt_local")).values("total")[:1]
        ),
        frs__currency__count=Subquery(
            frs_query.annotate(total=Count("currency", distinct=True)).values("total")[:1]
        ),
        max_fr_currency=MaxDistinct("frs__currency", output_field=CharField(), distinct=True),
    ))

    filters = (
        ('id', 'id'),
        ('number', 'number'),
        ('country_programme', 'agreement__country_programme'),
        ('section', 'sections__pk'),
        ('status', 'status'),
        ('partner', 'agreement__partner'),
        ('updated_before', 'modified__lte'),
        ('updated_after', 'modified__gte'),
    )

    def get_queryset(self, format=None):
        workspace = self.request.query_params.get('workspace', None)
        set_tenant_or_fail(workspace)
        return super().get_queryset()


class PRPPartnerListAPIView(ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPPartnerOrganizationListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    pagination_class = PRPPartnerPagination
    queryset = PartnerOrganization.objects.all()

    def get_queryset(self, format=None):
        query_params = self.request.query_params
        workspace = query_params.get('workspace', None)
        set_tenant_or_fail(workspace)
        return super().get_queryset()
