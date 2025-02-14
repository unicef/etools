from django.urls import path, include
from etools.applications.last_mile.admin_panel.views import *

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'locations', LocationsViewSet, basename='location')
router.register(r'user-locations', UserLocationsViewSet, basename='user-location')

app_name = "last_mile_admin"

urlpatterns = [
    path('', include(router.urls)),
]