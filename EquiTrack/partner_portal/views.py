__author__ = 'Robi'

from django.views.generic import FormView, TemplateView, View
from django.utils.http import urlsafe_base64_decode

class DashView(TemplateView):
    template_name = "partner_portal/dash.html"


class LoginFailedView(TemplateView):

    template_name = "partner_portal/loginfailed.html"

    def get_context_data(self, **kwargs):
        context = super(LoginFailedView, self).get_context_data(**kwargs)
        context['email'] = urlsafe_base64_decode(context['email'])
        return context
