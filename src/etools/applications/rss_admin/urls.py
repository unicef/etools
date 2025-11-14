from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.rss_admin.views import (
    AgreementRssViewSet,
    EngagementRssViewSet,
    EngagementAttachmentsRssViewSet,
    ReportAttachmentsRssViewSet,
    LocationSiteAdminViewSet,
    MonitoringActivityRssViewSet,
    PartnerOrganizationRssViewSet,
    ProgrammeDocumentRssViewSet,
    ActionPointRssViewSet,
)

router = DefaultRouter()
router.register(r'partners', PartnerOrganizationRssViewSet, basename='rss-admin-partners')
router.register(r'agreements', AgreementRssViewSet, basename='rss-admin-agreements')
router.register(r'programme-documents', ProgrammeDocumentRssViewSet, basename='rss-admin-programme-documents')
router.register(r'engagements', EngagementRssViewSet, basename='rss-admin-engagements')
router.register(
    r'engagements/(?P<engagement_pk>\d+)/engagement-attachments',
    EngagementAttachmentsRssViewSet,
    basename='rss-admin-engagement-attachments'
)
router.register(
    r'engagements/(?P<engagement_pk>\d+)/report-attachments',
    ReportAttachmentsRssViewSet,
    basename='rss-admin-report-attachments'
)
router.register(r'action-points', ActionPointRssViewSet, basename='rss-admin-action-points')
router.register(r'sites', LocationSiteAdminViewSet, basename='rss-admin-sites')
router.register(r'monitoring-activities', MonitoringActivityRssViewSet, basename='rss-admin-monitoring-activities')

app_name = 'rss_admin'

urlpatterns = [
    path('', include(router.urls)),
]
