from django.conf.urls import include, url

from rest_framework_nested import routers

from .views import PSEAViewSet

root_api = routers.SimpleRouter()

root_api.register(r'psea', PSEAViewSet, basename='psea')


app_name = 'psea'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
