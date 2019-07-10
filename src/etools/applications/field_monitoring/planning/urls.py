from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.planning.views import YearPlanViewSet

root_api = routers.SimpleRouter()
root_api.register(r'year-plan', YearPlanViewSet, base_name='year-plan')

app_name = 'field_monitoring_planning'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
