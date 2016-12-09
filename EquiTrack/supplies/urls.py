__author__ = 'unicef'

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import SuppliesDashboardView


urlpatterns = patterns(
    '',
    url(r'^$', login_required(SuppliesDashboardView.as_view()), name='supplies_dashboard'),
    # url(r'^app/$', 'winter.views.send_apk', name='winter_app'),
    # url(r'^data/$', login_required(SiteListJson.as_view()), name='winter_site_list'),
)
