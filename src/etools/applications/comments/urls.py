from django.urls import include, path

from rest_framework_nested import routers

from etools.applications.comments.views import CommentsViewSet

app_name = 'comments'

root_api = routers.SimpleRouter()
root_api.register(r'(?P<related_app>[^/]+)/(?P<related_model>[^/]+)/(?P<related_id>\d+)', CommentsViewSet,
                  basename='comments')


urlpatterns = [
    path('', include(root_api.urls)),
]
