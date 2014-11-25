__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from .views import WinterDashboardView


urlpatterns = patterns(
    '',
    url(r'^$', WinterDashboardView.as_view(), name='winter_dashboard'),
)