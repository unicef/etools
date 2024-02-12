from django.urls import include, path

from rest_framework_nested import routers

from etools.applications.last_mile import views

app_name = 'last_mile'

root_api = routers.SimpleRouter()
root_api.register(r'points-of-interest', views.PointOfInterestViewSet, basename='pois')
root_api.register(r'transfers', views.TransferViewSet, basename='transfers')
root_api.register(r'shipments', views.ShipmentUpdateView, basename='shipment-update')

urlpatterns = [
    path('', include(root_api.urls)),
]
