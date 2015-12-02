__author__ = 'Robi'

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from EquiTrack.utils import partner_required


from .views import (
    DashView
)




urlpatterns = patterns(
    '',
    url(r'$', partner_required(DashView.as_view())),

)
