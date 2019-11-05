from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.fm_settings import views

root_api = routers.SimpleRouter()
root_api.register(r'methods', views.MethodsViewSet, base_name='methods')
root_api.register(r'attachments', views.FieldMonitoringGeneralAttachmentsViewSet, base_name='general-attachments')
root_api.register(r'log-issues', views.LogIssuesViewSet, base_name='log-issues')
root_api.register(r'sites', views.LocationSitesViewSet, base_name='sites')
root_api.register(r'locations', views.FMLocationsViewSet, base_name='locations')
root_api.register(r'categories', views.CategoriesViewSet, base_name='categories')
root_api.register(r'questions', views.QuestionsViewSet, base_name='questions')

log_issues_api = NestedComplexRouter(root_api, r'log-issues')
log_issues_api.register(r'attachments', views.LogIssueAttachmentsViewSet, base_name='log-issue-attachments')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^interventions/(?P<intervention_pk>[0-9]+)/locations', views.InterventionLocationsView.as_view(),
        name='intervention-locations'),
    url(r'^results', views.ResultsViewSet.as_view(), name='results-list'),
    url(r'^locations/country', views.LocationsCountryView.as_view(), name='locations-country'),
    url(r'^', include(log_issues_api.urls)),
    url(r'^', include(root_api.urls)),
]
