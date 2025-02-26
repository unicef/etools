from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.last_mile.admin_panel.views import (
    AlertNotificationViewSet,
    AlertTypeListView,
    LocationsViewSet,
    OrganizationListView,
    ParentLocationListView,
    PointOfInterestTypeListView,
    TransferEvidenceListView,
    TransferHistoryListView,
    TransferItemViewSet,
    UserLocationsViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'alert-types', AlertTypeListView, basename='alert-type')
router.register(r'locations', LocationsViewSet, basename='location')
router.register(r'locations-type', PointOfInterestTypeListView, basename='location-type')
router.register(r'user-locations', UserLocationsViewSet, basename='user-location')
router.register(r'alert-notifications', AlertNotificationViewSet, basename='alert-notification')
router.register(r'stock-management', TransferItemViewSet, basename='stock-management')
router.register(r'organizations', OrganizationListView, basename='organizations-admin')
router.register(r'parent-locations', ParentLocationListView, basename='parent-locations')
router.register(r'reversal-of-partner-transactions', TransferHistoryListView, basename='transfer-history')
router.register(r'transfer-evidence', TransferEvidenceListView, basename='transfer-evidence')

app_name = "last_mile_admin"

urlpatterns = [
    path('', include(router.urls)),
]
