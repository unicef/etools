from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.admin_panel.views import (
    AlertNotificationViewSet,
    AlertTypeListView,
    ItemStockManagementView,
    LocationsViewSet,
    MaterialListView,
    OrganizationListView,
    ParentLocationListView,
    PartnerOrganizationListView,
    PointOfInterestCoordinateListView,
    PointOfInterestsLightViewSet,
    PointOfInterestTypeListView,
    TransferEvidenceListView,
    TransferHistoryListView,
    TransferItemViewSet,
    TransferReverseView,
    UpdateUserProfileViewSet,
    UserLocationsViewSet,
    UserPermissionsListView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename=USER_ADMIN_PANEL)
router.register(r'update-user-profile', UpdateUserProfileViewSet, basename=UPDATE_USER_PROFILE_ADMIN_PANEL)
router.register(r'alert-types', AlertTypeListView, basename=ALERT_TYPES_ADMIN_PANEL)
router.register(r'locations', LocationsViewSet, basename=LOCATIONS_ADMIN_PANEL)
router.register(r'coordinates', PointOfInterestCoordinateListView, basename=GEOPOINT_LOCATIONS)
router.register(r'locations-type', PointOfInterestTypeListView, basename=LOCATIONS_TYPE_ADMIN_PANEL)
router.register(r'user-locations', UserLocationsViewSet, basename=USER_LOCATIONS_ADMIN_PANEL)
router.register(r'alert-notifications', AlertNotificationViewSet, basename=ALERT_NOTIFICATIONS_ADMIN_PANEL)
router.register(r'stock-management', TransferItemViewSet, basename=STOCK_MANAGEMENT_ADMIN_PANEL)
router.register(r'stock-management-items', ItemStockManagementView, basename=UPDATE_ITEM_STOCK_ADMIN_PANEL)
router.register(r'organizations', OrganizationListView, basename='organizations-admin')
router.register(r'user-permissions', UserPermissionsListView, basename='user-permissions')
router.register(r'parent-locations', ParentLocationListView, basename=PARENT_LOCATIONS_ADMIN_PANEL)
router.register(r'reversal-of-partner-transactions', TransferHistoryListView, basename=TRANSFER_HISTORY_ADMIN_PANEL)
router.register(r'transfer-evidence', TransferEvidenceListView, basename=TRANSFER_EVIDENCE_ADMIN_PANEL)
router.register(r'materials', MaterialListView, basename=STOCK_MANAGEMENT_MATERIALS_ADMIN_PANEL)
router.register(r'partner-organizations', PartnerOrganizationListView, basename=PARTNER_ORGANIZATIONS_ADMIN_PANEL)
router.register(r'point-of-interests', PointOfInterestsLightViewSet, basename=POINT_OF_INTERESTS_LIGHT_DATA)
router.register(r'transfer', TransferReverseView, basename=TRANSFER_REVERSE_ADMIN_PANEL)

app_name = ADMIN_PANEL_APP_NAME

urlpatterns = [
    path('', include(router.urls)),
]
