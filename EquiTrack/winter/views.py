__author__ = 'jcranwellward'

import os

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.core.servers.basehttp import FileWrapper


class WinterDashboardView(TemplateView):

    template_name = 'winter/dashboard.html'


@login_required
def send_apk(request):

    filename = os.path.join(settings.STATIC_ROOT, 'app/UniSupply.apk')

    wrapper = FileWrapper(file(filename))
    response = HttpResponse(wrapper)
    response['Content-Length'] = os.path.getsize(filename)
    response['Content-Type'] = 'application/vnd.android.package-archive'
    response['Content-Disposition'] = 'inline; filename={}'.format(os.path.basename(filename))
    return response