from django.conf.urls import url
from django.urls import include

from rest_framework import routers

from etools.applications.management.views.general import InvalidateCache, SyncCountries, SyncFRs
from etools.applications.management.views.reports import LoadResultStructure
from etools.applications.management.views.sections import SectionsManagementView
from etools.applications.management.views.tasks_endpoints import (
    PMPIndicatorsReportView,
    SyncAllUsers,
    SyncDeltaUsers,
    TestSendEmailAPIView,
    UpdateAggregateHactValuesAPIView,
    UpdateHactValuesAPIView,
    UsersReportView,
)
from etools.applications.management.views.v1 import ActiveUsers, AgreementsStatisticsView, PortalDashView

router = routers.DefaultRouter()
router.register(r'sections', SectionsManagementView, base_name='sections_management')

app_name = 'management'


urlpatterns = ((
    url(r'^$', PortalDashView.as_view(), name='dashboard'),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    url(r'^sync-frs/$', SyncFRs.as_view(), name='sync_frs'),
    url(r'^sync-countries/$', SyncCountries.as_view(), name='sync_frs'),
    url(r'^api/stats/usercounts/$', ActiveUsers.as_view(), name='stats_user_counts'),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats_agreements'),
    url(r'^tasks/sync_all_users/$', SyncAllUsers.as_view(), name='tasks_sync_all_users'),
    url(r'^tasks/sync_delta_users/$', SyncDeltaUsers.as_view(), name='tasks_sync_delta_users'),
    url(r'^tasks/update_hact_values/$', UpdateHactValuesAPIView.as_view(), name='tasks_update_hact_values'),
    url(r'^tasks/update_aggregate_hact_values/$', UpdateAggregateHactValuesAPIView.as_view(),
        name='tasks_aggregate_update_hact_values'),
    url(r'^tasks/send_test_email/$', TestSendEmailAPIView.as_view(), name='tasks_send_test_email'),
    url(r'^reports/users/$', UsersReportView.as_view(), name='reports_users'),
    url(r'^reports/pmp_indicators/$', PMPIndicatorsReportView.as_view(), name='reports_pmp_indicators'),
    url(r'^', include(router.urls)),
), 'management')
