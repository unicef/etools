from django.urls import re_path

from etools.applications.environment.views import ActiveFlagAPIView

app_name = 'environment'
urlpatterns = (
    re_path(r'^flags/$',
            view=ActiveFlagAPIView.as_view(http_method_names=['get']),
            name='api-flags-list'),
)
