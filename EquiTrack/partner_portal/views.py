__author__ = 'Robi'

from django.views.generic import FormView, TemplateView, View
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponse
from django.conf import settings
# class DashView(TemplateView):
#     template_name = "partner_portal/dash.html"


class PortalDashView(View):

    def get(self, request):
        # not serving this as a static file in case in the future we want to be able to change versions
        with open(settings.SITE_ROOT + '/templates/partner_portal/index.html', 'r') as my_f:
            result = my_f.read()

        return HttpResponse(result)

class PortalLoginFailedView(TemplateView):

    template_name = "partner_portal/loginfailed.html"

    def get_context_data(self, **kwargs):
        context = super(PortalLoginFailedView, self).get_context_data(**kwargs)
        context['email'] = urlsafe_base64_decode(context['email'])
        return context
