from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.conf.urls import patterns, url, include

from .views import (
    LocationView,
    PcaView
)


urlpatterns = patterns(
    '',
    url(r'locations/$', LocationView.as_view(), name='locations'),
    url(r'pcas/$', PcaView.as_view(), name='pcas'),

    # auth and registration for partners
    url(r'', include('registration.auth_urls')),
)
