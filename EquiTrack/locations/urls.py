__author__ = 'jcranwellward'

from django.conf.urls import patterns, url

from djgeojson.views import GeoJSONLayerView

from .models import Governorate, Region, Locality


urlpatterns = patterns(
    '',
    url(r'^governorates.geojson$', GeoJSONLayerView.as_view(model=Governorate), name='governorates'),
    url(r'^districts.geojson$', GeoJSONLayerView.as_view(model=Region), name='districts'),
    url(r'^sub-districts.geojson$', GeoJSONLayerView.as_view(model=Locality), name='sub-districts'),
)