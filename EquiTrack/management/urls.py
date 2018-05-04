from __future__ import absolute_import

from django.conf.urls import url

from management.views.general import InvalidateCache, SyncFRs
from management.views.reports import LoadResultStructure
from management.views.v1 import ActiveUsersSection, AgreementsStatisticsView, PortalDashView

app_name = 'management'
urlpatterns = ((
    url(r'^$', PortalDashView.as_view(), name='dashboard'),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    url(r'^sync-frs/$', SyncFRs.as_view(), name='sync_frs'),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view(), name='stats_user_counts'),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats_agreements'),
), 'management')
