from django.conf.urls import url
from django.views.generic import TemplateView

from users.views import (
    ChangeUserCountryView,
    MyProfileAPIView,
    ProfileEdit,
    StaffUsersView,
    UserAuthAPIView,
    UsersDetailAPIView,
)

urlpatterns = (
    # api
    url(r'^api/profile/$', UserAuthAPIView.as_view(), name="user-api-profile"),
    url(r'^api/changecountry/$', ChangeUserCountryView.as_view(), name="country-change"),
    url(r'^api/$', StaffUsersView.as_view()),
    url(r'^api/(?P<pk>\d+)/$', UsersDetailAPIView.as_view(http_method_names=['get']), name="user-detail"),
    url(r'^myprofile/$', MyProfileAPIView.as_view(), name="myprofile-detail"),

    # user profile
    url(r'^profile_view/$', ProfileEdit.as_view(), name='user_profile'),

    url(r'^profile_view/complete/$',
        TemplateView.as_view(
            template_name='users/profile_change_done.html'),
        name='profile_complete'),
)
