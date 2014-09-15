__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import TripsView, TripsByOfficeView, TripsDashboard


urlpatterns = patterns(
    '',
    url(r'approved/$', TripsView.as_view()),
    url(r'offices/$', TripsByOfficeView.as_view()),
    url(r'/$', TripsDashboard.as_view()),
)