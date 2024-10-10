from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.governments.filters import PartnerNameOrderingFilter
from etools.applications.governments.models import GDD
from etools.applications.governments.serializers.gov_intervention import InterventionListSerializer, \
    InterventionCreateUpdateSerializer, MinimalInterventionListSerializer, InterventionDetailSerializer
from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.filters import InterventionEditableByFilter
from etools.applications.partners.views.interventions_v2 import InterventionListAPIView
from etools.applications.partners.views.interventions_v3 import PMPInterventionListCreateView, \
    PMPInterventionRetrieveUpdateView
from etools.libraries.djangolib.fields import CURRENCY_LIST


class GovInterventionListCreateView(PMPInterventionListCreateView):
    permission_classes = (IsAuthenticated,)  # TODO PMPInterventionPermission)
    search_terms = (
        'title__icontains',
        'partner__organization__name__icontains',
        'number__icontains',
        'cfei_number__icontains',
    )
    filter_backends = InterventionListAPIView.filter_backends + (
        InterventionEditableByFilter,
        OrderingFilter,
        PartnerNameOrderingFilter
    )
    ordering_fields = ('number', 'status', 'title', 'start', 'end')

    def get_serializer_class(self):
        if self.request.method == "GET":
            query_params = self.request.query_params
            # if "format" in query_params.keys():
            #     export_format = query_params.get("format")
            #     if export_format == "csv":
            #         return InterventionExportSerializer
            #     elif export_format == "csv_flat":
            #         return InterventionExportFlatSerializer
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return MinimalInterventionListSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        return InterventionListSerializer

    def get_queryset(self):
        qs = GDD.objects.frs_qs().filter(partner_organization__organization__organization_type=OrganizationType.GOVERNMENT)\

        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        planned_budget = request.data.get("planned_budget")
        super().create(request, *args, **kwargs)

        # check if setting currency
        if planned_budget and planned_budget.get("currency"):
            currency = planned_budget.get("currency")
            if currency not in CURRENCY_LIST:
                raise ValidationError(f"Invalid currency: {currency}.")
            self.instance.planned_budget.currency = currency
            self.instance.planned_budget.save()

        return Response(
            InterventionDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )


class GovInterventionRetrieveUpdateView(PMPInterventionRetrieveUpdateView):
    pass
