
from django.conf.urls import url

from .views import (
    ProfileEdit,
    ChangeUserCountryView,
    UsersDetailAPIView,
    MyProfileAPIView
)
from .views_v2 import UsersListApiView


urlpatterns = (
    # api
    url(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post'])),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get'])),
    url(r'^', UsersListApiView.as_view()),  # TODO: staff required , partners should not be able to hit this

)