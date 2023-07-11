from django.urls import include, path, re_path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.travel import views
from etools.applications.travel.views import TravelStaticDropdownsListAPIView

root_api = routers.SimpleRouter()

root_api.register(
    r'trip',
    views.TripViewSet,
    basename='trip',
)

itinerary_item_api = NestedComplexRouter(root_api, r'trip')
itinerary_item_api.register(
    r'itinerary_item',
    views.ItineraryItemViewSet,
    basename='itinerary_item',
)

trip_attachments_api = NestedComplexRouter(root_api, r'trip')
trip_attachments_api.register(
    r'attachments',
    views.TripAttachmentsViewSet,
    basename='trip-attachments',
)

activity_api = NestedComplexRouter(root_api, r'trip')
activity_api.register(
    r'activity',
    views.ActivityViewSet,
    basename='activity',
)

report_api = NestedComplexRouter(root_api, r'trip')
report_api.register(
    r'report',
    views.ReportViewSet,
    basename='report',
)

report_attachments_api = NestedComplexRouter(report_api, r'report')
report_attachments_api.register(
    r'attachments',
    views.ReportAttachmentsViewSet,
    basename='report-attachments',
)

app_name = 'travel'

urlpatterns = [
    path('', include(root_api.urls)),
    path('', include(itinerary_item_api.urls)),
    path('', include(trip_attachments_api.urls)),
    path('', include(activity_api.urls)),
    path('', include(report_api.urls)),
    path('', include(report_attachments_api.urls)),
    re_path(r'^static-data/$',
            view=TravelStaticDropdownsListAPIView.as_view(http_method_names=['get']),
            name='travel-static-data'),
]
