from django.urls import re_path

from .views.gis_v1 import GisLocationsGeomDetailsViewset, GisLocationsGeomListViewset, GisLocationsInUseViewset

app_name = 'management_gis'

urlpatterns = [
    # gis URLs
    re_path(r'^in-use/$', GisLocationsInUseViewset.as_view(), name='locations-gis-in-use'),
    re_path(r'^locations-geom/$', GisLocationsGeomListViewset.as_view(), name='locations-gis-geom-list'),
    re_path(
        r'^locations-geom/pcode/(?P<pcode>\w+)/$',
        GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-pcode'
    ),
    re_path(
        r'^locations-geom/id/(?P<id>\w+)/$',
        GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-id'
    ),
]
