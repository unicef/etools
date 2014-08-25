__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import (
    LocationView,
    ValidatePCANumberView,
    CreateFACERequestView
)


urlpatterns = patterns(
    '',
    url(r'pca/location/$', LocationView.as_view(), name='locations'),
    url(r'pca/validate/$', ValidatePCANumberView.as_view()),
    url(r'face/create/$', CreateFACERequestView.as_view())
)
