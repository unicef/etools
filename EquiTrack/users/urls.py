
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
    url(r'^api/profile/$', UserAuthAPIView.as_view()),
    url(r'^api/changecountry/$', ChangeUserCountryView.as_view(http_method_names=['post'])),
    url(r'^api/(?P<pk>[0-9]+)/$', UsersDetailAPIView.as_view(http_method_names=['get'])),
    url(r'^api/viewset/(?P<pk>\d+)/$', user_detail, name='user-detail'),
    url(r'^api/viewset/', user_list, name='user-list'),
    url(r'^api/', UsersView.as_view()),  # TODO: staff required , partners should not be able to hit this
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),
    url(r'^country/$', CountryView.as_view(http_method_names=['get']), name="country-detail"),


    # user profile
    url(r'^profile_view/$', ProfileEdit.as_view(), name='user_profile'),

    url(r'^profile_view/complete/$',
        TemplateView.as_view(
            template_name='users/profile_change_done.html'),
        name='profile_complete'),
)
