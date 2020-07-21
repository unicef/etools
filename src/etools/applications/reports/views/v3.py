from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import Section
from etools.applications.reports.serializers.v1 import SectionCreateSerializer


class PMPSectionViewSet(
        PMPBaseViewMixin,
        QueryStringFilterMixin,
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    queryset = Section.objects
    permission_classes = [IsAuthenticated]  # TODO open for development
    serializer_class = SectionCreateSerializer
    filters = (
        ('active', 'active'),
    )

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to sections that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(interventions__in=self.pds())
        return qs
