__author__ = 'Robi'

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from EquiTrack.utils import partner_required


from .views import (
    PortalDashView,
    PortalLoginFailedView,
)




urlpatterns = patterns(
    '',
    #url(r'^$', partner_required(DashView.as_view())),
    url(r'^$', PortalDashView.as_view()),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),



)
