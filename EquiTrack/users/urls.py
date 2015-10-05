__author__ = 'jcranwellward'

from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from .views import EquiTrackRegistrationView, UserAuthAPIView, ProfileEdit, UsersView


urlpatterns = patterns(
    '',

    # registration
    # url(r'^activate/complete/$',
    #     TemplateView.as_view(
    #         template_name='registration/activation_complete.html'),
    #     name='registration_activation_complete'),
    # # Activation keys get matched by \w+ instead of the more specific
    # # [a-fA-F0-9]{40} because a bad activation key should still get to the
    # # view; that way it can return a sensible "invalid key" message instead of
    # # a confusing 404.
    # url(r'^activate/(?P<activation_key>\w+)/$',
    #     ActivationView.as_view(),
    #     name='registration_activate'),
    url(r'^register/$',
        EquiTrackRegistrationView.as_view(),
        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),

    #api
    url(r'^profile/', UserAuthAPIView.as_view()),
    url(r'^$', UsersView.as_view()),

    #user profile
    url(r'^profile_view/$', ProfileEdit.as_view(), name='user_profile'),

    url(r'^profile_view/complete/$',
        TemplateView.as_view(
            template_name='registration/profile_change_done.html'),
            name='profile_complete'),
)