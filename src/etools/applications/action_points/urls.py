from django.urls import include, re_path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.action_points.views import (
    ActionPointCommentsViewSet,
    ActionPointViewSet,
    CategoryViewSet,
    CommentSupportingDocumentsViewSet,
)

app_name = 'action-points'

action_points_api = routers.SimpleRouter()
action_points_api.register(r'action-points', ActionPointViewSet, basename='action-points')
action_points_api.register(r'categories', CategoryViewSet, basename='categories')

action_point_comments_api = NestedComplexRouter(action_points_api, r'action-points')
action_point_comments_api.register(r'comments', ActionPointCommentsViewSet, basename='comments')

comment_attachments_api = NestedComplexRouter(action_point_comments_api, r'comments')
comment_attachments_api.register(r'supporting-documents', CommentSupportingDocumentsViewSet, basename='supporting-documents')


urlpatterns = [
    re_path(r'^', include(comment_attachments_api.urls)),
    re_path(r'^', include(action_point_comments_api.urls)),
    re_path(r'^', include(action_points_api.urls)),
]
