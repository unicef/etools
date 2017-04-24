__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from locations import views


urlpatterns = patterns(
    '',
    url(r'^cartodbtables/$', views.CartoDBTablesView.as_view(), name='cartodbtables'),
    url(r'^autocomplete/$', views.LocationQuerySetView.as_view(), name='locations_autocomplete'),

    # TODO: test performance
    url(
        r'^autocomplete-light/$',
        views.LocationAutocompleteView.as_view(),
        name='locations-autocomplete-light',
    )
)
