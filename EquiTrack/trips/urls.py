__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import TripsView


urlpatterns = patterns(
    '',
    url(r'approved/$', TripsView.as_view()),
)