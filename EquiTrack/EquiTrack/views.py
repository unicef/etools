__author__ = 'jcranwellward'

from django.views.generic import TemplateView

from partners.models import PCA
from reports.models import Sector


class DashboardView(TemplateView):

    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):

        sectors = {}
        for sector in Sector.objects.all():
            indicators = sector.indicator_set.all()
            if not indicators:
                continue
            sectors[sector.name] = [
                indicator for indicator in indicators
            ]

        return {
            'sectors': sectors,
            'pcas': {
                'active': PCA.objects.filter(status='active').count(),
                'implemented': PCA.objects.filter(status='implemented').count(),
                'in_process': PCA.objects.filter(status='in_process').count(),
                'cancelled': PCA.objects.filter(status='active').count(),
            }
        }