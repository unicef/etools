from django.urls import include, re_path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.planning import views

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', views.YearPlanViewSet, basename='year-plan')
root_api.register(r'questions/templates/(?P<level>\w+)(?:/target/(?P<target_id>\d+))?', views.TemplatedQuestionsViewSet,
                  basename='question-templates')
root_api.register(r'activities', views.MonitoringActivitiesViewSet, basename='activities')
root_api.register(r'users', views.FMUsersViewSet, basename='users')
root_api.register(r'cp-outputs', views.CPOutputsViewSet, basename='cp_outputs')
root_api.register(r'interventions', views.InterventionsViewSet, basename='interventions')
root_api.register(r'partners', views.PartnersViewSet, basename='partners')

activities_api = NestedComplexRouter(root_api, r'activities', lookup='monitoring_activity')
activities_api.register(r'attachments', views.ActivityAttachmentsViewSet, basename='activity_attachments')
activities_api.register(r'action-points', views.MonitoringActivityActionPointViewSet, basename='activity_action_points')
activities_api.register(r'tpm-concerns', views.TPMConcernsViewSet, basename='activity_tpm_concerns')

app_name = 'field_monitoring_planning'
urlpatterns = [
    re_path(r'^', include(activities_api.urls)),
    re_path(r'^', include(root_api.urls)),
]
