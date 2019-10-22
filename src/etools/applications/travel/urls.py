from django.urls import include, path

from rest_framework_nested import routers

from etools.applications.travel import views

root_api = routers.SimpleRouter()

root_api.register(
    r'itinerary',
    views.ItineraryViewSet,
    basename='itinerary',
)

app_name = 'travel'
urlpatterns = [
    path('', include(root_api.urls)),
]
