from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.data_collection.routers import NestedBulkRouter
from etools.applications.field_monitoring.planning import views

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', views.YearPlanViewSet, basename='year-plan')
root_api.register(r'questions/templates/(?P<level>\w+)(?:/target/(?P<target_id>\d+))?', views.TemplatedQuestionsViewSet,
                  basename='question-templates')
root_api.register(r'activities', views.MonitoringActivitiesViewSet, basename='activities')
root_api.register(r'users', views.FMUsersViewSet, basename='users')
root_api.register(r'cp-outputs', views.CPOutputsViewSet, basename='cp_outputs')
root_api.register(r'interventions', views.InterventionsViewSet, basename='interventions')

activities_api = NestedBulkRouter(root_api, r'activities')
activities_api.register(r'attachments', views.ActivityAttachmentsViewSet, basename='activity-attachments')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(activities_api.urls)),
    url(r'^', include(root_api.urls)),
]
