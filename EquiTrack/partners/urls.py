from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.conf.urls import patterns, url, include

from .views import (
    LocationView,
    PortalDashView,
    PortalLoginFailedView,
)


urlpatterns = patterns(
    '',
    url(r'^$', PortalDashView.as_view()),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'locations/$', LocationView.as_view(), name='locations'),

    # auth and registration for partners
    #url(r'', include('registration.auth_urls')),
)
