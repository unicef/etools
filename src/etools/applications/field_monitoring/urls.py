from django.conf.urls import include, url

from rest_framework_nested import routers

from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.views import (
    MethodsViewSet,
    MethodTypesViewSet
)

root_api = routers.SimpleRouter()
root_api.register(r'methods', MethodsViewSet, base_name='methods')

method_types_api = NestedComplexRouter(root_api, r'methods', lookup='method')
method_types_api.register(r'types', MethodTypesViewSet, base_name='method-types')

app_name = 'field_monitoring'
urlpatterns = [
    url(r'^', include(method_types_api.urls)),
    url(r'^', include(root_api.urls)),
]
