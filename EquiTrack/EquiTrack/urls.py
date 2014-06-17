from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

import autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from .views import (
    MapView,
    DashboardView,
    EquiTrackRegistrationView
)

urlpatterns = patterns(
    '',
    url(r'^$', login_required(DashboardView.as_view()), name='dashboard'),
    # url(r'^map/$', login_required(MapView.as_view()), name='map'),


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

    # auth
    url(r'', include('registration.auth_urls')),

    url(r'partners/', include('partners.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # helper urls
    url(r'^chaining/', include('smart_selects.urls')),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)
