from django.db import transaction

from rest_framework import status
from rest_framework.response import Response

from etools.applications.partners.views.interventions_v2 import InterventionDetailAPIView, InterventionListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin


class PMPInterventionMixin(PMPBaseViewMixin):
    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(agreement__partner__in=self.partners())
        return qs


class PMPInterventionListCreateView(PMPInterventionMixin, InterventionListAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") in ["csv", "csv_flat"]:
                    return self.map_serializer(query_params.get("format"))
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return self.map_serializer("list_min")
        if self.request.method == "POST":
            return self.map_serializer("create")
        return self.map_serializer("list")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            self.map_serializer("detail")(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )


class PMPInterventionRetrieveUpdateView(PMPInterventionMixin, InterventionDetailAPIView):
    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return self.map_serializer("create")
        return self.map_serializer("detail")

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            self.map_serializer("detail")(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )
