from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.action_points.views import ActionPointViewSet

app_name = 'action-points'

action_points_api = routers.SimpleRouter()
action_points_api.register(r'action-points', ActionPointViewSet, base_name='action-points')


urlpatterns = [
    url(r'^', include(action_points_api.urls)),
]
