__author__ = 'unicef'

from django.conf.urls import patterns, url


from .views import (
    TripsByOfficeView,
    TripsDashboard,
    AppsTemplateView,
    AppsIOSTemplateView,
    AppsAndroidTemplateView,
    AppsIOSPlistView,
    TripUploadPictureView
)

urlpatterns = patterns(
    '',
    url(r'^apps/$', AppsTemplateView.as_view(), name="etrips_apps"),
    url(r'^apps/ios/$', AppsIOSTemplateView.as_view()),
    url(r'^apps/android/$', AppsAndroidTemplateView.as_view()),
    url(r'^api/(?P<trip>\d+)/upload/$', TripUploadPictureView.as_view()),
    url(r'^api/apps/ios/etrips.plist$', AppsIOSPlistView.as_view(), name="eTrips_plist"),
    url(r'^offices/$', TripsByOfficeView.as_view()),
    url(r'^$', TripsDashboard.as_view(), name='trips_dashboard'),

)
