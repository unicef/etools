from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import (
    LocationView,
    PcaView,
    PcaPDFView
)


urlpatterns = patterns(
    '',
    url(r'locations/$', LocationView.as_view(), name='locations'),
    url(r'pcas/$', PcaView.as_view(), name='pcas'),
    url(r'agreement/pdf/(?P<agr>\d+)', PcaPDFView.as_view()),
)
