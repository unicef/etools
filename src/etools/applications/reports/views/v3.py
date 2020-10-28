from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.partners.models import InterventionResultLink
from etools.applications.partners.permissions import UserIsPartnerStaffMemberPermission, UserIsStaffPermission
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import Office, Section
from etools.applications.reports.serializers.v1 import SectionCreateSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.reports.views.v2 import ResultFrameworkView, SpecialReportingRequirementListCreateView


class PMPOfficeViewSet(
        PMPBaseViewMixin,
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    serializer_class = OfficeSerializer
    queryset = Office.objects

    def get_queryset(self):
        qs = super().get_queryset()
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

        # if partner, limit to offices that they are associated with via PD
        if self.is_partner_staff():
            qs = qs.filter(office_interventions__in=self.pds())
        return qs


class PMPSectionViewSet(
        PMPBaseViewMixin,
        QueryStringFilterMixin,
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    queryset = Section.objects
    serializer_class = SectionCreateSerializer
    filters = (
        ('active', 'active'),
    )

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to sections that they are associated with via PD
        if self.is_partner_staff():
            qs = qs.filter(interventions__in=self.pds())
        return qs


class PMPSpecialReportingRequirementListCreateView(
        PMPBaseViewMixin,
        SpecialReportingRequirementListCreateView,
):
    """Wrapper for Special Reporting Requirement View"""


class PMPResultFrameworkView(PMPBaseViewMixin, ResultFrameworkView):
    permission_classes = [UserIsStaffPermission | UserIsPartnerStaffMemberPermission]

    def get_queryset(self, format=None):
        qs = InterventionResultLink.objects.filter(
            intervention=self.kwargs.get("pk")
        )
        if self.is_partner_staff():
            qs = qs.filter(
                intervention__agreement__partner__in=self.partners(),
                intervention__date_sent_to_partner__isnull=False,
            )

        data = []
        for result_link in qs:
            data.append(result_link)
            for ll_result in result_link.ll_results.all():
                data += ll_result.applied_indicators.all()
        return data
