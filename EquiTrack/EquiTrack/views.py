__author__ = 'jcranwellward'

from django.views.generic import TemplateView

from partners.models import PCA, PartnerOrganization, PCASectorOutput
from reports.models import Sector, ResultStructure, Indicator
from locations.models import CartoDBTable, GatewayType, Governorate, Region
from funds.models import Donor


class DashboardView(TemplateView):

    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):

        sectors = {}
        sructure = self.request.GET.get('structure', 1)
        try:
            current_structure = ResultStructure.objects.get(id=sructure)
        except ResultStructure.DoesNotExist:
            current_structure = None
        for sector in Sector.objects.all():
            indicators = sector.indicator_set.filter(
                view_on_dashboard=True,
            )
            if current_structure:
                indicators = indicators.filter(
                    result_structure=current_structure
                )
            if not indicators:
                continue

            sectors[sector.name] = []
            for indicator in indicators:
                programmed = indicator.programmed(
                    result_structure=current_structure
                )
                sectors[sector.name].append(
                    {
                        'indicator': indicator,
                        'programmed': programmed
                    }
                )

        return {
            'sectors': sectors,
            'current_structure': current_structure,
            'structures': ResultStructure.objects.all(),
            'pcas': {
                'active': PCA.get_active_partnerships().count(),
                'implemented': PCA.objects.filter(
                    status=PCA.IMPLEMENTED,
                    amendment_number=0,
                ).count(),
                'in_process': PCA.objects.filter(
                    status=PCA.IN_PROCESS,
                ).count(),
                'cancelled': PCA.objects.filter(
                    status=PCA.CANCELLED,
                    amendment_number=0,
                ).count(),
            }
        }


class MapView(TemplateView):

    template_name = 'map.html'

    def get_context_data(self, **kwargs):
        return {
            'tables': CartoDBTable.objects.all(),
            'gateway_list': GatewayType.objects.all(),
            'governorate_list': Governorate.objects.all(),
            'sectors_list': Sector.objects.all(),
            'result_structure_list': ResultStructure.objects.all(),
            'region_list': Region.objects.all(),
            'partner_list': PartnerOrganization.objects.all(),
            'indicator_list': Indicator.objects.all(),
            'output_list': PCASectorOutput.objects.all(),
            'donor_list': Donor.objects.all()
        }
