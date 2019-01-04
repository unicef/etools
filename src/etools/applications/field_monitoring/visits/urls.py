from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.visits.views import VisitsViewSet, VisitMethodTypesViewSet

root_api = routers.SimpleRouter()
root_api.register(r'visits', VisitsViewSet, base_name='visits')

visits_api = NestedComplexRouter(root_api, r'visits', lookup='visit')
visits_api.register(r'method-types', VisitMethodTypesViewSet, base_name='visit-method-types')

app_name = 'field_monitoring_visits'
urlpatterns = [
    url(r'^', include(visits_api.urls)),
    url(r'^', include(root_api.urls)),
]
