from django.urls import re_path

from etools.applications.users.views import (
    ChangeUserCountryView,
    ChangeUserRoleView,
    MyProfileAPIView,
    StaffUsersView,
    UsersDetailAPIView,
)

app_name = 'users'
urlpatterns = (
    # api
    re_path(r'^api/changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    re_path(r'^api/user_management/$', ChangeUserRoleView.as_view(http_method_names=['post']), name="user-change"),
    re_path(r'^api/$', StaffUsersView.as_view()),
    re_path(r'^api/(?P<pk>\d+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    re_path(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
)
