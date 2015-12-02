__author__ = 'Robi'

from django.views.generic import FormView, TemplateView, View


class DashView(TemplateView):
    template_name = "partner_portal/dash.html"

