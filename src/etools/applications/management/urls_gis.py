from django.conf.urls import url

from .views.gis_v1 import GisLocationsGeomDetailsViewset, GisLocationsGeomListViewset, GisLocationsInUseViewset

urlpatterns = [
    # gis URLs
    url(r'^in-use/$', GisLocationsInUseViewset.as_view(), name='locations-gis-in-use'),
    url(r'^locations-geom/$', GisLocationsGeomListViewset.as_view(), name='locations-gis-geom-list'),
    url(
        r'^locations-geom/pcode/(?P<pcode>\w+)/$',
        GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-pcode'
    ),
    url(
        r'^locations-geom/id/(?P<id>\w+)/$',
        GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-id'
    ),
]
