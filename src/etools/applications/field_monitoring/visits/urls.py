from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.visits.views import (
    VisitMethodTypesViewSet, VisitsCPOutputConfigsViewSet, VisitsLocationsViewSet, VisitsPartnersViewSet,
    VisitsTeamMembersViewSet, VisitsViewSet, VisitsLocationSitesViewSet)

root_api = routers.SimpleRouter()
root_api.register(r'visits/partners', VisitsPartnersViewSet, base_name='visits-partners')
root_api.register(r'visits/cp-outputs/configs', VisitsCPOutputConfigsViewSet, base_name='visits-cp-output-configs')
root_api.register(r'visits/locations', VisitsLocationsViewSet, base_name='visits-locations')
root_api.register(r'visits/locations/sites', VisitsLocationSitesViewSet, base_name='visits-location-sites')
root_api.register(r'visits/team-members', VisitsTeamMembersViewSet, base_name='visits-team-members')
root_api.register(r'visits', VisitsViewSet, base_name='visits')

visits_api = NestedComplexRouter(root_api, r'visits', lookup='visit')
visits_api.register(r'method-types', VisitMethodTypesViewSet, base_name='visit-method-types')

app_name = 'field_monitoring_visits'
urlpatterns = [
    url(r'^', include(visits_api.urls)),
    url(r'^', include(root_api.urls)),
]
