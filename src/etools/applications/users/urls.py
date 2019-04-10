from django.conf.urls import url

from etools.applications.users.views import (
    ChangeUserCountryView,
    MyProfileAPIView,
    StaffUsersView,
    UserAuthAPIView,
    UsersDetailAPIView,
)

app_name = 'users'
urlpatterns = (
    # api
    url(r'^api/profile/$', UserAuthAPIView.as_view(), name="user-api-profile"),
    url(r'^api/changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    url(r'^api/$', StaffUsersView.as_view()),
    url(r'^api/(?P<pk>\d+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
)
