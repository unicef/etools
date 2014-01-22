__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import SectorView


urlpatterns = patterns(
    '',

    url(r'sectors/$', SectorView.as_view()),

)
