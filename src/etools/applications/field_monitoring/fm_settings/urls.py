from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.fm_settings.views import *

root_api = routers.SimpleRouter()
root_api.register(r'methods', MethodsViewSet, base_name='methods')
root_api.register(r'sites', LocationSitesViewSet, base_name='sites')

# root_api.register(r'checklist/categories', CheckListCategoriesViewSet, base_name='checklist-categories')
# root_api.register(r'checklist', CheckListViewSet, base_name='checklist-items')

# root_api.register(r'log-issues', LogIssuesViewSet, base_name='log-issues')

root_api.register(r'attachments', FieldMonitoringGeneralAttachmentsViewSet, base_name='general-attachments')
root_api.register(r'locations', FMLocationsViewSet, base_name='locations')

# log_issues_api = NestedComplexRouter(root_api, r'log-issues')
# log_issues_api.register(r'attachments', LogIssueAttachmentsViewSet, base_name='log-issue-attachments')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^interventions/(?P<intervention_pk>[0-9]+)/locations', InterventionLocationsView.as_view(),
        name='intervention-locations'),
    url(r'^results', ResultsViewSet.as_view(), name='results-list'),
    url(r'^locations/country', LocationsCountryView.as_view(), name='locations-country'),
    # url(r'^', include(cp_outputs_configs_api.urls)),
    # url(r'^', include(log_issues_api.urls)),
    url(r'^', include(root_api.urls)),
]
