from django.conf.urls import url

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

urlpatterns = [
    url(r'^$', PortalDashView.as_view()),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view()),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view()),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view()),
]
