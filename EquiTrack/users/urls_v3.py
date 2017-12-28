from django.conf.urls import url

from views_v3 import (
    ChangeUserCountryView,
    CountryView,
    MyProfileAPIView,
    UsersDetailAPIView,
    UsersListAPIView,
)

urlpatterns = (
    # api
    url(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post']), name="country-change"),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^$', UsersListAPIView.as_view(), name="users-list"),
)
