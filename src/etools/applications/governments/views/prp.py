from django.db.models import CharField, Count, OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.funds.models import FundsReservationHeader
from etools.applications.governments.models import GDD
from etools.applications.governments.permissions import ReadOnlyAPIUser
from etools.applications.governments.serializers.prp import GDDFileSerializer, PRPGDDListSerializer
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.permissions import ListCreateAPIMixedPermission
from etools.applications.partners.views.helpers import set_tenant_or_fail
from etools.applications.partners.views.prp_v1 import PRPInterventionPagination
from etools.libraries.djangolib.models import MaxDistinct


class PRPGDDListAPIView(QueryStringFilterMixin, ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPGDDListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    filter_backends = (PartnerScopeFilter,)
    pagination_class = PRPInterventionPagination

    frs_query = FundsReservationHeader.objects.filter(
        gdd=OuterRef("pk")
    ).order_by().values("gdd")

    queryset = GDD.objects.filter(
        Q(status=GDD.DRAFT, date_sent_to_partner__isnull=False) | ~Q(status=GDD.DRAFT),
        in_amendment=False,
    ).prefetch_related(
        'result_links__cp_output',
        'result_links__gdd_key_interventions',
        'result_links__gdd_key_interventions__ewp_key_intervention__cp_key_intervention',
        'result_links__gdd_key_interventions__result_link__cp_output__cp_output',
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
    )

    filters = (
        ('id', 'id'),
        ('number', 'number'),
        ('country_programme', 'country_programme'),
        ('section', 'sections__pk'),
        ('status', 'status'),
        ('partner', 'partner'),
        ('updated_before', 'modified__lte'),
        ('updated_after', 'modified__gte'),
    )

    def get_queryset(self, format=None):
        workspace = self.request.query_params.get('workspace', None)
        set_tenant_or_fail(workspace)
        return super().get_queryset()


class PRPGDDFileView(APIView):
    permission_classes = (ReadOnlyAPIUser,)

    def get(self, request, gdd_pk):

        workspace = request.query_params.get('workspace', None)
        set_tenant_or_fail(workspace)

        gdd = get_object_or_404(GDD, pk=gdd_pk)

        return Response(GDDFileSerializer(gdd).data)
