from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.rss_admin.views import (
    AgreementRssViewSet,
    PartnerOrganizationRssViewSet,
    ProgrammeDocumentRssViewSet,
    ActionPointRssViewSet,
)

router = DefaultRouter()
router.register(r'partners', PartnerOrganizationRssViewSet, basename='rss-admin-partners')
router.register(r'agreements', AgreementRssViewSet, basename='rss-admin-agreements')
router.register(r'programme-documents', ProgrammeDocumentRssViewSet, basename='rss-admin-programme-documents')
router.register(r'action-points', ActionPointRssViewSet, basename='rss-admin-action-points')

app_name = 'rss_admin'

urlpatterns = [
    path('', include(router.urls)),
]
