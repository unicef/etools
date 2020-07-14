from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.comments.views import CommentsViewSet

app_name = 'comments'

root_api = routers.SimpleRouter()
root_api.register(r'(?P<related_app>[^/]+)/(?P<related_model>[^/]+)/(?P<related_id>\d+)/comments', CommentsViewSet,
                  basename='comments')


urlpatterns = [
    url(r'^', include(root_api.urls)),
]
