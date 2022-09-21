from django.urls import include, re_path

from rest_framework_nested import routers

from etools.applications.users.views import ADUserAPIView
from etools.applications.users.views_v3 import (
    ChangeUserCountryView,
    ChangeUserOrganizationView,
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
    re_path(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    re_path(r'^changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    re_path(r'^changeorganization/$', ChangeUserOrganizationView.as_view(), name="organization-change"),
    re_path(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    re_path(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    re_path(r'^AD/(?P<username>.*)$', ADUserAPIView.as_view(http_method_names=['get', ]), name="ad-user-api-view"),
    re_path(r'^', include(root_api.urls)),
    re_path(r'^$', UsersListAPIView.as_view(), name="users-list"),
)
