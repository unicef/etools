__author__ = 'jcranwellward'

from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from .views import TripsView, TripsByOfficeView


urlpatterns = patterns(
    '',
    url(r'approved/$', TripsView.as_view()),
    url(r'offices/$', TripsByOfficeView.as_view()),
    url(r'$', TemplateView.as_view(
            template_name='trips/dashboard.html'
        ),
        name='trips_dashboard'
    ),
)