__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import TripsApprovedView, \
    TripsByOfficeView, TripsDashboard, \
    TripsListApi, TripActionView, \
    TripDetailsView, PlaygroundView


urlpatterns = patterns(
    '',
    url(r'^approved/$', TripsApprovedView.as_view()),
    url(r'^playground/$', PlaygroundView.as_view()),
    url(r'api/list/$', TripsListApi.as_view()),
    url(r'api/(?P<trip>\d+)/(?P<action>\D+)/$', TripActionView.as_view()),
    url(r'api/(?P<trip>\d+)/$', TripDetailsView.as_view()),
    url(r'offices/$', TripsByOfficeView.as_view()),
    url(r'^$', TripsDashboard.as_view(), name='trips_dashboard'),
)