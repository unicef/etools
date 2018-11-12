from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.visits.views import UNICEFVisitsViewSet, VisitsViewSet


root_api = routers.SimpleRouter()
root_api.register(r'visits/unicef/', UNICEFVisitsViewSet, base_name='visits-unicef')
root_api.register(r'visits/', VisitsViewSet, base_name='visits')

app_name = 'field_monitoring_visits'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
