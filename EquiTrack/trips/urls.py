__author__ = 'jcranwellward'

from django.conf.urls import patterns, url


from .views import (
    TripsByOfficeView,
    TripsDashboard,
    AppsTemplateView,
    AppsIOSTemplateView,
    AppsAndroidTemplateView,
    AppsIOSPlistView,

    # TODO: remove these when eTrips application was rolled out
    TripsListApi,
    TripActionView,
    TripDetailsView,
    TripUploadPictureView,
)

urlpatterns = patterns(
    '',
    url(r'^apps/$', AppsTemplateView.as_view(), name="etrips_apps"),
    url(r'^apps/ios/$', AppsIOSTemplateView.as_view()),
    url(r'^apps/android/$', AppsAndroidTemplateView.as_view()),
    url(r'^api/apps/ios/etrips.plist$', AppsIOSPlistView.as_view(), name="eTrips_plist"),
    url(r'^offices/$', TripsByOfficeView.as_view()),
    url(r'^$', TripsDashboard.as_view(), name='trips_dashboard'),

    # TODO: remove these when eTrips application was rolled out
    url(r'^api/list/$', TripsListApi.as_view()),
    url(r'^api/(?P<trip>\d+)/upload/$', TripUploadPictureView.as_view()),
    url(r'^api/(?P<trip>\d+)/(?P<action>\D+)/$', TripActionView.as_view()),
    url(r'^api/(?P<trip>\d+)/$', TripDetailsView.as_view()),

)