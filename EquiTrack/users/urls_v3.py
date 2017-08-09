
from django.conf.urls import url

from .views import (
    ChangeUserCountryView,
)
from views_v3 import UsersListApiView, UsersDetailAPIView, CountryView, MyProfileAPIView


urlpatterns = (
    # api
    url(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post'])),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get'])),
    url(r'^', UsersListApiView.as_view()),  # TODO: staff required , partners should not be able to hit this
)
