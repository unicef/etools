__author__ = 'jcranwellward'

from django.views.generic import TemplateView

from partners.models import PCA
from reports.models import Sector


class DashboardView(TemplateView):

    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):

        sectors = {}
        for sector in Sector.objects.all():
            indicators = sector.indicator_set.filter(
                view_on_dashboard=True
            )
            if not indicators:
                continue
            sectors[sector.name] = [
                indicator for indicator in indicators
            ]

        return {
            'sectors': sectors,
            'pcas': {
                'active': PCA.objects.filter(
                    status='active',
                    amendment_number=0,
                ).count(),
                'implemented': PCA.objects.filter(
                    status='implemented',
                    amendment_number=0,
                ).count(),
                'in_process': PCA.objects.filter(
                    status='in_process',
                    amendment_number=0,
                ).count(),
                'cancelled': PCA.objects.filter(
                    status='cancelled',
                    amendment_number=0,
                ).count(),
            }
        }