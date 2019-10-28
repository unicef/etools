from django.urls import include, path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.travel import views

root_api = routers.SimpleRouter()

root_api.register(
    r'itinerary',
    views.ItineraryViewSet,
    basename='itinerary',
)

itinerary_item_api = NestedComplexRouter(root_api, r'itinerary')
itinerary_item_api.register(
    r'item',
    views.ItineraryItemViewSet,
    base_name='item',
)

activity_api = NestedComplexRouter(root_api, r'itinerary')
activity_api.register(
    r'activity',
    views.ActivityViewSet,
    base_name='activity',
)

action_points_api = NestedComplexRouter(
    activity_api,
    r'activity',
    lookup='travel',
)
action_points_api.register(
    r'action-points',
    views.ActivityActionPointViewSet,
    base_name='action-points',
)

report_api = NestedComplexRouter(root_api, r'itinerary')
report_api.register(
    r'report',
    views.ReportViewSet,
    base_name='report',
)

report_attachments_api = NestedComplexRouter(report_api, r'report')
report_attachments_api.register(
    r'attachments',
    views.ReportAttachmentsViewSet,
    base_name='report-attachments',
)


app_name = 'travel'
urlpatterns = [
    path('', include(root_api.urls)),
    path('', include(itinerary_item_api.urls)),
    path('', include(activity_api.urls)),
    path('', include(action_points_api.urls)),
    path('', include(report_api.urls)),
    path('', include(report_attachments_api.urls)),
]
