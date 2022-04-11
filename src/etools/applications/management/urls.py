from django.urls import include, re_path

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
router.register(r'sections', SectionsManagementView, basename='sections_management')

app_name = 'management'


urlpatterns = ((
    re_path(r'^$', PortalDashView.as_view(), name='dashboard'),
    re_path(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    re_path(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    re_path(r'^sync-frs/$', SyncFRs.as_view(), name='sync_frs'),
    re_path(r'^sync-countries/$', SyncCountries.as_view(), name='sync_frs'),
    re_path(r'^api/stats/usercounts/$', ActiveUsers.as_view(), name='stats_user_counts'),
    re_path(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats_agreements'),
    re_path(r'^tasks/sync_all_users/$', SyncAllUsers.as_view(), name='tasks_sync_all_users'),
    re_path(r'^tasks/sync_delta_users/$', SyncDeltaUsers.as_view(), name='tasks_sync_delta_users'),
    re_path(r'^tasks/update_hact_values/$', UpdateHactValuesAPIView.as_view(), name='tasks_update_hact_values'),
    re_path(r'^tasks/update_aggregate_hact_values/$', UpdateAggregateHactValuesAPIView.as_view(),
            name='tasks_aggregate_update_hact_values'),
    re_path(r'^tasks/send_test_email/$', TestSendEmailAPIView.as_view(), name='tasks_send_test_email'),
    re_path(r'^reports/users/$', UsersReportView.as_view(), name='reports_users'),
    re_path(r'^reports/pmp_indicators/$', PMPIndicatorsReportView.as_view(), name='reports_pmp_indicators'),
    re_path(r'^', include(router.urls)),
), 'management')
