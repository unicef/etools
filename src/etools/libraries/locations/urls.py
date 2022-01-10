from django.urls import re_path

from rest_framework import routers

from .views import (
    CartoDBTablesView,
    LocationQuerySetView,
    LocationsLightViewSet,
    LocationsViewSet,
    LocationTypesViewSet,
)

api = routers.SimpleRouter()

api.register(r'locations', LocationsViewSet, basename='locations')
api.register(r'locations-light', LocationsLightViewSet, basename='locations-light')
api.register(r'locations-types', LocationTypesViewSet, basename='locationtypes')

urlpatterns = [
    re_path(r'^cartodbtables/$', CartoDBTablesView.as_view(), name='cartodbtables'),
    re_path(r'^autocomplete/$', LocationQuerySetView.as_view(), name='locations_autocomplete'),
]
