from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.planning import views

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', views.YearPlanViewSet, base_name='year-plan')
root_api.register(r'questions/templates/(?P<level>\w+)(?:/target/(?P<target_id>\d+))?', views.TemplatedQuestionsViewSet,
                  base_name='question-templates')
root_api.register(r'activities', views.MonitoringActivitiesViewSet, base_name='activities')
root_api.register(r'users', views.FMUsersViewSet, base_name='users')

activities_api = NestedComplexRouter(root_api, r'activities')
activities_api.register(r'attachments', views.ActivityAttachmentsViewSet, base_name='activity-attachments')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(activities_api.urls)),
    url(r'^', include(root_api.urls)),
]
