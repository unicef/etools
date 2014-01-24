__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import (
    SectorView,
    LocationView,
    PartnerView,

)


urlpatterns = patterns(
    '',
    url(r'sector/$', SectorView.as_view()),
    url(r'partner/$', PartnerView.as_view()),
    url(r'location/$', LocationView.as_view()),
)
