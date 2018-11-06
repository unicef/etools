from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.planning.views import (
    YearPlanViewSet,
    YearPlanAttachmentsViewSet,
    TaskViewSet)

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', YearPlanViewSet, base_name='year-plan')

year_plan_nested_api = NestedComplexRouter(root_api, r'year-plan', lookup='year_plan')
year_plan_nested_api.register(r'attachments', YearPlanAttachmentsViewSet, base_name='year-plan-attachments')
year_plan_nested_api.register(r'tasks', TaskViewSet, base_name='year-plan-tasks')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(year_plan_nested_api.urls)),
    url(r'^', include(root_api.urls)),
]
