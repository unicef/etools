
from django.conf.urls import patterns, url

from .views import (
    MyProfileAPIView,
)


urlpatterns = patterns(
    '',
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),

)
