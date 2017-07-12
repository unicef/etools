from django.conf.urls import patterns, url

from management.views.reports import (
    LoadResultStructure,
)
from management.views.general import (
    InvalidateCache,
)
from management.views.v1 import (
    ActiveUsersSection,
    TripsStatisticsView,
    AgreementsStatisticsView,
    PortalDashView,
)

urlpatterns = patterns(
    '',
    url(r'^$', PortalDashView.as_view(), name='dashboard'),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load-results'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate-cache'),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view(), name='stats-usercounts'),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view(), name='stats-trips'),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats-agreements'),
)
