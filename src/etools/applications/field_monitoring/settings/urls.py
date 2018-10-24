from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.settings.views import (
    CPOutputConfigsViewSet,
    MethodsViewSet,
    MethodTypesViewSet,
    LocationSitesViewSet,
)

root_api = routers.SimpleRouter()
root_api.register(r'methods', MethodsViewSet, base_name='methods')
root_api.register(r'methods/types', MethodTypesViewSet, base_name='method-types')
root_api.register(r'sites', LocationSitesViewSet, base_name='sites')
root_api.register(r'cp-outputs', CPOutputConfigsViewSet, base_name='cp_output-configs')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
