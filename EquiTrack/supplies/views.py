from django.db.models import F, Sum
from django.views.generic import TemplateView

from partners.models import DistributionPlan


class SuppliesDashboardView(TemplateView):

    template_name = 'supplies/dashboard.html'

    def get_context_data(self, **kwargs):
        plans = DistributionPlan.objects.filter(sent=True)
        return {
            'distributions': plans.count(),
            'completed': plans.filter(quantity=F('delivered')).count(),
            'supplies_planned': plans.aggregate(Sum('quantity')).values()[0],
            'supplies_delivered': plans.aggregate(Sum('delivered')).values()[0]
        }
