from django.urls import include, re_path

from rest_framework_nested import routers

from etools.applications.action_points.views import ActionPointViewSet, CategoryViewSet

app_name = 'action-points'

action_points_api = routers.SimpleRouter()
action_points_api.register(r'action-points', ActionPointViewSet, basename='action-points')
action_points_api.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    re_path(r'^', include(action_points_api.urls)),
]
