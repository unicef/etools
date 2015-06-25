from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

import autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from users.views import EquiTrackRegistrationView
from .views import (
    MapView,
    DashboardView,
    UserDashboardView,
    CmtView
)

urlpatterns = patterns(
    '',
    url(r'^$', login_required(UserDashboardView.as_view()), name='dashboard'),
    url(r'^indicators', login_required(DashboardView.as_view()), name='indicator_dashboard'),
    url(r'^map/$', login_required(MapView.as_view()), name='map'),
    url(r'^cmt/$', login_required(CmtView.as_view()), name='cmt'),


    url(r'locations/', include('locations.urls')),
    url(r'partners/', include('partners.urls')),
    url(r'trips/', include('trips.urls')),
    url(r'users/', include('users.urls')),

    # auth
    url(r'', include('registration.auth_urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # helper urls
    url(r'^messages/', include('messages_extends.urls')),
    url(r'^chaining/', include('smart_selects.urls')),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)
