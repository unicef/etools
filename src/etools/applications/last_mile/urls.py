from django.urls import include, path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.last_mile import views, views_ext

app_name = 'last_mile'

root_api = routers.SimpleRouter()
root_api.register(r'points-of-interest', views.PointOfInterestViewSet, basename='pois')
root_api.register(r'poi-types', views.PointOfInterestTypeViewSet, basename='poi-types')
root_api.register(r'items', views.ItemUpdateViewSet, basename='item-update')

transfer_api = NestedComplexRouter(root_api, r'points-of-interest', lookup='point_of_interest')
transfer_api.register(r'transfers', views.TransferViewSet, basename='transfers')

transfer_api.register(r'materials', views.InventoryMaterialsViewSet, basename='materials')

urlpatterns = [
    path('', include(root_api.urls)),
    path('', include(transfer_api.urls)),
    path(
        'import-materials/',
        view=views_ext.VisionIngestMaterialsApiView.as_view(http_method_names=['post'], ),
        name="vision-ingest-materials"
    ),
    path(
        'import-transfers/',
        view=views_ext.VisionIngestTransfersApiView.as_view(http_method_names=['post'],),
        name="vision-ingest-transfers"
    ),
    path(
        'points-of-interest/<int:poi_pk>/items/',
        view=views.InventoryItemListView.as_view(http_method_names=['get'],),
        name='inventory-item-list',
    ),
]
