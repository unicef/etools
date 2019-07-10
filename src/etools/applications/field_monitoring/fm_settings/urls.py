from django.conf.urls import include, url

from rest_framework_nested import routers

# from unicef_restlib.routers import NestedComplexRouter
from etools.applications.field_monitoring.fm_settings.views import (
    FieldMonitoringGeneralAttachmentsViewSet,
    InterventionLocationsView,
    MethodsViewSet,
)

root_api = routers.SimpleRouter()
root_api.register(r'methods', MethodsViewSet, base_name='methods')
root_api.register(r'attachments', FieldMonitoringGeneralAttachmentsViewSet, base_name='general-attachments')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^interventions/(?P<intervention_pk>[0-9]+)/locations', InterventionLocationsView.as_view(),
        name='intervention-locations'),
    url(r'^', include(root_api.urls)),
]
