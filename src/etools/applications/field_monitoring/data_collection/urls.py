from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.data_collection import views

root_api = routers.SimpleRouter()
root_api.register(r'activities', views.ActivityDataCollectionViewSet, base_name='methods')

activities_api = NestedComplexRouter(root_api, r'activities')
activities_api.register(r'attachments', views.ActivityReportAttachmentsViewSet, base_name='activity-report-attachments')

app_name = 'field_monitoring_data_collection'
urlpatterns = [
    url(r'^', include(activities_api.urls)),
    url(r'^', include(root_api.urls)),
]
