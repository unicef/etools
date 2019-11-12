from django.conf.urls import url

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
    url(r'^cartodbtables/$', CartoDBTablesView.as_view(), name='cartodbtables'),
    url(r'^autocomplete/$', LocationQuerySetView.as_view(), name='locations_autocomplete'),
]
