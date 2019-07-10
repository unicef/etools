from django.conf.urls import include, url

from rest_framework_nested import routers

from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.planning.views import (
    LogIssuesViewSet,
    LogIssueAttachmentsViewSet,
    YearPlanViewSet
)

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', YearPlanViewSet, base_name='year-plan')
root_api.register(r'log-issues', LogIssuesViewSet, base_name='log-issues')

log_issues_api = NestedComplexRouter(root_api, r'log-issues')
log_issues_api.register(r'attachments', LogIssueAttachmentsViewSet, base_name='log-issue-attachments')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(log_issues_api.urls)),
    url(r'^', include(root_api.urls)),
]
