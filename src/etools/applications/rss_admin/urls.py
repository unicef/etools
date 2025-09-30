from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.rss_admin.views import AgreementAdminViewSet, PartnerOrganizationAdminViewSet

router = DefaultRouter()
router.register(r'partners', PartnerOrganizationAdminViewSet, basename='rss-admin-partners')
router.register(r'agreements', AgreementAdminViewSet, basename='rss-admin-agreements')

app_name = 'rss_admin'

urlpatterns = [
    path('', include(router.urls)),
]
