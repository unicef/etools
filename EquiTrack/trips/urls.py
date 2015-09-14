__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import TripsApprovedView, TripsByOfficeView, TripsDashboard, TripsApi, TripActionView


urlpatterns = patterns(
    '',
    url(r'approved/$', TripsApprovedView.as_view()),
    url(r'api/$', TripsApi.as_view()),
    #url(r'api/(?P<trip>\d+)/(?P<action>\D+)/$', TripActionView.as_view()),
    url(r'api/(?P<trip>\d+)/$', TripActionView.as_view()),
    url(r'offices/$', TripsByOfficeView.as_view()),
    url(r'^$', TripsDashboard.as_view(), name='trips_dashboard'),
)