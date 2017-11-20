from django.conf.urls import url
from views_v3 import CountryView, MyProfileAPIView, UsersDetailAPIView, UsersListApiView

from users.views import ChangeUserCountryView

urlpatterns = (
    # api
    url(r'^profile/$', MyProfileAPIView.as_view(http_method_names=['get', 'patch']), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post'])),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="v3-user-country-details"),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get'])),
    url(r'^', UsersListApiView.as_view()),  # TODO: staff required , partners should not be able to hit this
)
