from django.shortcuts import get_object_or_404

from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import intervention_field_is_editable_permission
from etools.applications.partners.views.interventions_v3 import DetailedInterventionResponseMixin
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import Office, Section
from etools.applications.reports.serializers.v1 import SectionCreateSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.reports.views.v2 import (
    SpecialReportingRequirementListCreateView,
    SpecialReportingRequirementRetrieveUpdateDestroyView,
)
from etools.libraries.djangolib.views import ExternalModuleFilterMixin


class PMPOfficeViewSet(
        PMPBaseViewMixin,
        ExternalModuleFilterMixin,
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    serializer_class = OfficeSerializer
    queryset = Office.objects
    module2filters = {
        "pmp": ['office_interventions__partner_focal_points__user', ]
    }

    def get_queryset(self):
        qs = super().get_queryset(module="pmp")
        if "values" in self.request.query_params.keys():
            # Used for ghost data - filter in all(), and return straight away.
            try:
                ids = [
                    int(x)
                    for x in self.request.query_params.get("values").split(",")
                ]
            except ValueError:
                raise ValidationError("ID values must be integers")
            else:
                qs = qs.filter(pk__in=ids)
        return qs


class PMPSectionViewSet(
        PMPBaseViewMixin,
        ExternalModuleFilterMixin,
        QueryStringFilterMixin,
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    queryset = Section.objects
    serializer_class = SectionCreateSerializer
    module2filters = {
        "pmp": ['interventions__partner_focal_points__user', ]
    }
    filters = (
        ('active', 'active'),
    )

    def get_queryset(self, format=None):
        return super().get_queryset(module="pmp")


class PMPSpecialReportingRequirementListCreateView(
        PMPBaseViewMixin,
        DetailedInterventionResponseMixin,
        SpecialReportingRequirementListCreateView,
):
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('reporting_requirements')),
    ]

    def get_root_object(self):
        return get_object_or_404(Intervention.objects, pk=self.kwargs.get('intervention_pk'))

    def get_intervention(self):
        return self.get_root_object()


class PMPSpecialReportingRequirementRetrieveUpdateDestroyView(
    PMPBaseViewMixin,
    DetailedInterventionResponseMixin,
    SpecialReportingRequirementRetrieveUpdateDestroyView,
):
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('reporting_requirements')),
    ]

    def get_root_object(self):
        return get_object_or_404(Intervention.objects, pk=self.kwargs.get('intervention_pk'))

    def get_intervention(self):
        return self.get_root_object()
