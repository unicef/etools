__author__ = 'jcranwellward'

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import WinterDashboardView, SiteListJson


urlpatterns = patterns(
    '',
    url(r'^$', login_required(WinterDashboardView.as_view()), name='winter_dashboard'),
    url(r'^app/$', 'winter.views.send_apk', name='winter_app'),
    url(r'^data/$', login_required(SiteListJson.as_view()), name='winter_site_list'),
)