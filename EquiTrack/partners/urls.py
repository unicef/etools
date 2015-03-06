__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import (
    LocationView,
    ValidatePCANumberView,
    CreateFACERequestView,
    PartnersView

)


urlpatterns = patterns(
    '',
    url(r'pca/location/$', LocationView.as_view(), name='locations'),
    url(r'pca/info/$', PartnersView.as_view(), name='partners'),
    url(r'pca/validate/$', ValidatePCANumberView.as_view()),
    url(r'face/create/$', CreateFACERequestView.as_view())
)
