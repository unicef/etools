from django.conf.urls import url

from djgeojson.views import GeoJSONLayerView

from locations import views


urlpatterns = (
    url(r'^cartodbtables/$', views.CartoDBTablesView.as_view(), name='cartodbtables'),
    url(r'^autocomplete/$', views.LocationQuerySetView.as_view(), name='locations_autocomplete'),

    # TODO: test performance
    url(
        r'^autocomplete-light/$',
        views.LocationAutocompleteView.as_view(),
        name='locations-autocomplete-light',
    )
)
