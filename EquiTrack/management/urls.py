__author__ = 'RobertAvram'


from django.conf.urls import patterns, url

from .views import (
    ActiveUsersSection,
    TripsStatisticsView
)

urlpatterns = patterns(
    '',
    url(r'^api/usercounts/$', ActiveUsersSection.as_view()),
    url(r'^api/tripstatistics/$', TripsStatisticsView.as_view()),
    url(r'^api/agreementstatistics/$', TripsStatisticsView.as_view()),
    url(r'^api/interventionstatistics/$', TripsStatisticsView.as_view()),
)
