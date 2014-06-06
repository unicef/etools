from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

import autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from .views import DashboardView

urlpatterns = patterns(
    '',
    url(r'^$', login_required(DashboardView.as_view()), name='dashboard'),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'admin/login.html'}),

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
