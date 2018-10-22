from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.views import (
    MethodsViewSet,
    MethodTypesViewSet,
    LocationsViewSet,
    SitesViewSet)

root_api = routers.SimpleRouter()
root_api.register(r'methods', MethodsViewSet, base_name='methods')
root_api.register(r'methods/types', MethodTypesViewSet, base_name='method-types')
root_api.register(r'locations', LocationsViewSet, base_name='locations')
root_api.register(r'sites', SitesViewSet, base_name='sites')

app_name = 'field_monitoring'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
