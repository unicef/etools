__author__ = 'RobertAvram'

from django.conf.urls import patterns, url

from management.views.reports import (
    LoadResultStructure,
)

from management.views.v1 import (
    ActiveUsersSection,
    TripsStatisticsView,
    AgreementsStatisticsView,
    InterventionsStatisticsView,
    PortalDashView,
)

urlpatterns = patterns(
    '',
    url(r'^$', PortalDashView.as_view()),
    url(r'^load-results/$', LoadResultStructure.as_view()),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view()),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view()),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view()),
    url(r'^api/stats/interventions/$', InterventionsStatisticsView.as_view()),

)

