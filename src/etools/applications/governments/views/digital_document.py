from django.db import transaction

from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.models import Intervention
from etools.applications.partners.views.interventions_v3 import PMPInterventionListCreateView, \
    PMPInterventionRetrieveUpdateView


class DigitalDocumentListCreateView(PMPInterventionListCreateView):
    ordering_fields = ('number', 'status', 'title', 'start', 'end')

    def get_queryset(self):
        qs = Intervention.objects.filter(agreement__partner__organization__organization_type=OrganizationType.GOVERNMENT)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # agreement
        # document_type
        # planned_budget = request.data.get("planned_budget")
        #
        #
        # # check if setting currency
        # if planned_budget and planned_budget.get("currency"):
        #     currency = planned_budget.get("currency")
        #     if currency not in CURRENCY_LIST:
        #         raise ValidationError(f"Invalid currency: {currency}.")
        #     self.instance.planned_budget.currency = currency
        #     self.instance.planned_budget.save()
        #
        # return Response(
        #     InterventionDetailSerializer(
        #         self.instance,
        #         context=self.get_serializer_context(),
        #     ).data,
        #     status=status.HTTP_201_CREATED,
        #     headers=self.headers
        # )
        return super().create(request, *args, **kwargs)


class DigitalDocumentRetrieveUpdateView(PMPInterventionRetrieveUpdateView):
    pass
