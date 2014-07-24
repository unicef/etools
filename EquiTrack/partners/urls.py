__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import (
    SectorView,
    LocationView,
    PartnerView,
    ValidatePCANumberView,
    CreateFACERequestView
)


urlpatterns = patterns(
    '',
    url(r'sector/$', SectorView.as_view()),
    url(r'partner/$', PartnerView.as_view()),
    url(r'location/$', LocationView.as_view(), name='locations'),
    url(r'pca/validate/$', ValidatePCANumberView.as_view()),
    url(r'face/create/$', CreateFACERequestView.as_view())
)
