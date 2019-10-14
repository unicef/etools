from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.users.views import ADUserAPIView
from etools.applications.users.views_v3 import (
    ChangeUserCountryView,
    CountryView,
    ExternalUserViewSet,
    MyProfileAPIView,
    UsersDetailAPIView,
    UsersListAPIView,
)

root_api = routers.SimpleRouter()
root_api.register(r'external', ExternalUserViewSet, basename='external')

app_name = 'users'
urlpatterns = (
    url(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^AD/(?P<username>.*)$', ADUserAPIView.as_view(http_method_names=['get', ]), name="ad-user-api-view"),
    url(r'^', include(root_api.urls)),
    url(r'^$', UsersListAPIView.as_view(), name="users-list"),
)
