from django.conf.urls import url

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
    url(r'^api/changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    url(r'^api/user_management/$', ChangeUserRoleView.as_view(http_method_names=['post']), name="user-change"),
    url(r'^api/$', StaffUsersView.as_view()),
    url(r'^api/(?P<pk>\d+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
)
