__author__ = 'RobertAvram'


from django.conf.urls import patterns, url

from .views import (
    ActiveUsersSection,
    TripsStatisticsView,
    AgreementsStatisticsView,
    InterventionsStatisticsView
)

urlpatterns = patterns(
    '',
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view()),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view()),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view()),
    url(r'^api/stats/interventions/$', InterventionsStatisticsView.as_view()),
)
