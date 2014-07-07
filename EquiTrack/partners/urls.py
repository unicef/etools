__author__ = 'jcranwellward'

from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page

from .views import (
    SectorView,
    LocationView,
    PartnerView,

)


urlpatterns = patterns(
    '',
    url(r'sector/$', SectorView.as_view()),
    url(r'partner/$', PartnerView.as_view()),
    url(r'location/$', LocationView.as_view(), name='locations'),
)
