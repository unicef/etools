
from django.conf.urls import url

from etools.applications.management.views.general import InvalidateCache, SyncFRs
from etools.applications.management.views.reports import LoadResultStructure
from etools.applications.management.views.tasks_endpoints import (TestSendEmailAPIView,
                                                                  UpdateAggregateHactValuesAPIView,
                                                                  UpdateHactValuesAPIView,)
from etools.applications.management.views.v1 import ActiveUsersSection, AgreementsStatisticsView, PortalDashView

app_name = 'management'
urlpatterns = ((
    url(r'^$', PortalDashView.as_view(), name='dashboard'),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    url(r'^sync-frs/$', SyncFRs.as_view(), name='sync_frs'),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view(), name='stats_user_counts'),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats_agreements'),
    url(r'^tasks/update_hact_values/$', UpdateHactValuesAPIView.as_view(), name='tasks_update_hact_values'),
    url(r'^tasks/update_aggregate_hact_values/$', UpdateAggregateHactValuesAPIView.as_view(),
        name='tasks_aggregate_update_hact_values'),
    url(r'^tasks/send_test_email/$', TestSendEmailAPIView.as_view(), name='tasks_send_test_email'),
), 'management')
