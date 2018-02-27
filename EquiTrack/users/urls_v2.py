from django.conf.urls import url

from users.views_v2 import (
    ChangeUserCountryView,
    CountriesViewSet,
    CountryView,
    MyProfileAPIView,
    StaffUsersView,
    UserAuthAPIView,
    UsersDetailAPIView,
)


urlpatterns = (
    url(r'^profile/$', UserAuthAPIView.as_view()),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post']), name="country-change"),
    url(r'^$', StaffUsersView.as_view()),
    url(r'^(?P<pk>\d)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    url(r'^workspaces', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
)
