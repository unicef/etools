__author__ = 'jcranwellward'

from django.views.generic import TemplateView

from partners.models import PCA
from reports.models import Sector, ResultStructure
from locations.models import CartoDBTable, GatewayType, Governorate
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.core import serializers

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
                'active': PCA.objects.filter(
                    status=PCA.ACTIVE,
                    amendment_number=0,
                ).count(),
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
            'governorate_list': Governorate.objects.all()
        }


class NikMapView(TemplateView):

    template_name = 'map_nik.html'

    def get_context_data(self, **kwargs):
        return {'gateway_list': GatewayType.objects.all(),
                'governorate_list': Governorate.objects.all(),
                'tables': CartoDBTable.objects.all()
                }


def all_json_governorates(request, gateway):
    current_gateway = GatewayType.objects.get(id=gateway)
    gs = Governorate.objects.all().filter(gateway=current_gateway)
    json_gs = serializers.serialize("json", gs)
    return HttpResponse(json_gs, mimetype="application/javascript")