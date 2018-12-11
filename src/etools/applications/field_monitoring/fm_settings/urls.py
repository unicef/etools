from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.fm_settings.views import (
    CheckListCategoriesViewSet, CheckListViewSet, CPOutputConfigsViewSet, CPOutputsViewSet, LocationSitesViewSet,
    FMMethodsViewSet, FMMethodTypesViewSet, PlannedCheckListItemViewSet, LogIssuesViewSet, LogIssueAttachmentsViewSet,
    MonitoredPartnersViewSet, LocationsCountryView, FieldMonitoringGeneralAttachmentsViewSet, ResultsViewSet,
    InterventionLocationsView)

root_api = routers.SimpleRouter()
root_api.register(r'methods/types', FMMethodTypesViewSet, base_name='method-types')
root_api.register(r'methods', FMMethodsViewSet, base_name='methods')
root_api.register(r'sites', LocationSitesViewSet, base_name='sites')
root_api.register(r'cp-outputs/configs', CPOutputConfigsViewSet, base_name='cp_output-configs')
root_api.register(r'cp-outputs/partners', MonitoredPartnersViewSet, base_name='monitored-partners')
root_api.register(r'cp-outputs', CPOutputsViewSet, base_name='cp_outputs')
root_api.register(r'checklist/categories', CheckListCategoriesViewSet, base_name='checklist-categories')
root_api.register(r'checklist', CheckListViewSet, base_name='checklist-items')
root_api.register(r'log-issues', LogIssuesViewSet, base_name='log-issues')
root_api.register(r'attachments', FieldMonitoringGeneralAttachmentsViewSet, base_name='general-attachments')

cp_outputs_configs_api = NestedComplexRouter(root_api, r'cp-outputs/configs', lookup='cp_output_config')
cp_outputs_configs_api.register(r'planned-checklist', PlannedCheckListItemViewSet, base_name='planned-checklist-items')

log_issues_api = NestedComplexRouter(root_api, r'log-issues')
log_issues_api.register(r'attachments', LogIssueAttachmentsViewSet, base_name='log-issue-attachments')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^interventions/(?P<intervention_pk>[0-9]+)/locations', InterventionLocationsView.as_view(),
        name='intervention-locations'),
    url(r'^results', ResultsViewSet.as_view(), name='results-list'),
    url(r'^locations/country', LocationsCountryView.as_view(), name='locations-country'),
    url(r'^', include(cp_outputs_configs_api.urls)),
    url(r'^', include(log_issues_api.urls)),
    url(r'^', include(root_api.urls)),
]
