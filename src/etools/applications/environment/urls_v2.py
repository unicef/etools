
from django.conf.urls import url

from etools.applications.environment.views import ActiveFlagAPIView

app_name = 'environment'
urlpatterns = (
    url(r'^flags/$',
        view=ActiveFlagAPIView.as_view(http_method_names=['get']),
        name='api-flags-list'),

)
