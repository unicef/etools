from django.conf.urls import url

from locations import views

urlpatterns = [
    # gis URLs
    url(r'^in-use/$', views.GisLocationsInUseViewset.as_view(), name='locations-gis-in-use'),
    url(r'^locations-geom/$', views.GisLocationsGeomListViewset.as_view(), name='locations-gis-geom-list'),
    url(
        r'^locations-geom/pcode/(?P<pcode>\w+)/$',
        views.GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-pcode'
    ),
    url(
        r'^locations-geom/id/(?P<id>\w+)/$',
        views.GisLocationsGeomDetailsViewset.as_view(),
        name='locations-gis-get-by-id'
    ),
]
