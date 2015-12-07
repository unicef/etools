__author__ = 'Robi'

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from EquiTrack.utils import partner_required


from .views import (
    DashView,
    LoginFailedView,
)




urlpatterns = patterns(
    '',
    #url(r'^$', partner_required(DashView.as_view())),
    url(r'^$', DashView.as_view()),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', LoginFailedView.as_view(), name='sociallogin_notamember'),



)
