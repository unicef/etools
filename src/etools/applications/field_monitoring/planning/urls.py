from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.planning.views import (
    YearPlanViewSet,
    YearPlanAttachmentsViewSet,
)

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', YearPlanViewSet, base_name='year-plan')

year_plan_attachments_api = NestedComplexRouter(root_api, r'year-plan')
year_plan_attachments_api.register(r'attachments', YearPlanAttachmentsViewSet, base_name='year-plan-attachments')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(year_plan_attachments_api.urls)),
    url(r'^', include(root_api.urls)),
]
