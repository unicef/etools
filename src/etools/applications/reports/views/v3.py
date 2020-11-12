from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import Office, Section
from etools.applications.reports.serializers.v1 import SectionCreateSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.reports.views.v2 import SpecialReportingRequirementListCreateView
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
        SpecialReportingRequirementListCreateView,
):
    """Wrapper for Special Reporting Requirement View"""
