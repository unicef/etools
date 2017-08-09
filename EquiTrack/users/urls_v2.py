from django.conf.urls import url

from .views import (
    MyProfileAPIView,
    CountryView
)


urlpatterns = (
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
)
