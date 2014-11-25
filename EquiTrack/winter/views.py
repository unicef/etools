__author__ = 'jcranwellward'

from django.views.generic import TemplateView


class WinterDashboardView(TemplateView):

    template_name = 'winter/dashboard.html'