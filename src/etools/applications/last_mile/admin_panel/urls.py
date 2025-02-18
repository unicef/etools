from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.last_mile.admin_panel.views import (
    AlertNotificationViewSet,
    LocationsViewSet,
    UserLocationsViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'locations', LocationsViewSet, basename='location')
router.register(r'user-locations', UserLocationsViewSet, basename='user-location')
router.register(r'alert-notifications', AlertNotificationViewSet, basename='alert-notification')

app_name = "last_mile_admin"

urlpatterns = [
    path('', include(router.urls)),
]
