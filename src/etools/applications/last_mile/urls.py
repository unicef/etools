from django.urls import include, path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.last_mile import views

app_name = 'last_mile'

root_api = routers.SimpleRouter()
root_api.register(r'points-of-interest', views.PointOfInterestViewSet, basename='pois')
root_api.register(r'poi-types', views.PointOfInterestTypeViewSet, basename='poi-types')
root_api.register(r'items', views.ItemUpdateViewSet, basename='poi-types')

transfer_api = NestedComplexRouter(root_api, r'points-of-interest', lookup='point_of_interest')
transfer_api.register(r'transfers', views.TransferViewSet, basename='transfers')

urlpatterns = [
    path('', include(root_api.urls)),
    path('', include(transfer_api.urls)),
]
