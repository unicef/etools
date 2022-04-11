from django.urls import re_path

from etools.applications.users.views_v2 import (
    ChangeUserCountryView,
    CountriesViewSet,
    CountryView,
    MyProfileAPIView,
    StaffUsersView,
    UsersDetailAPIView,
)

app_name = 'users'
urlpatterns = (
    re_path(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post']), name="country-change"),
    re_path(r'^$', StaffUsersView.as_view()),
    re_path(r'^(?P<pk>\d)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    re_path(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
    re_path(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    re_path(r'^workspaces', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
)
