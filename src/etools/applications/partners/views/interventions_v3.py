from django.db import transaction

from rest_framework import status
from rest_framework.response import Response

from etools.applications.partners.permissions import PartnershipManagerPermission
from etools.applications.partners.serializers.exports.interventions import (
    InterventionExportFlatSerializer,
    InterventionExportSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
    MinimalInterventionListSerializer,
)
from etools.applications.partners.views.interventions_v2 import InterventionListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin


class PMPInterventionListAPIView(PMPBaseViewMixin, InterventionListAPIView):
    permission_classes = (PartnershipManagerPermission,)

    SERIALIZER_MAP = {
        "default": (InterventionListSerializer, None),
        "create": (InterventionCreateUpdateSerializer, None),
        "list_min": (MinimalInterventionListSerializer, None),
        "csv": (InterventionExportSerializer, None),
        "csv_flat": (InterventionExportFlatSerializer, None),
        "detail": (InterventionDetailSerializer, None),
    }

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
        return self.map_serializer("default")

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(agreement__partner__in=self.partners())
        return qs

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
