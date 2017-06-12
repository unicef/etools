
from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from rest_framework_nested import routers
from .views import (
    UserAuthAPIView,
    ProfileEdit,
    UsersView,
    ChangeUserCountryView,
    UsersDetailAPIView,
    MyProfileAPIView,
    CountryView,
    UserViewSet,
)
user_list = UserViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
user_detail = UserViewSet.as_view({
    'get': 'retrieve',
})

urlpatterns = patterns(
    '',

    # api
    url(r'^profile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
    url(r'^changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post'])),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),
    url(r'^(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get'])),
    url(r'^full/(?P<pk>\d+)/$', user_detail, name='user-detail'),
    url(r'^full/', user_list, name='user-list'),
    url(r'^', UsersView.as_view()),  # TODO: staff required , partners should not be able to hit this



    # user profile
    url(r'^profile_view/$', ProfileEdit.as_view(), name='user_profile'),

    url(r'^profile_view/complete/$',
        TemplateView.as_view(
            template_name='users/profile_change_done.html'),
        name='profile_complete'),
)
