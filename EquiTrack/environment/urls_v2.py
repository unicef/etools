
from django.conf.urls import url

from environment.views import ActiveFlagAPIView

urlpatterns = (
    url(r'^flags/$',
        view=ActiveFlagAPIView.as_view(http_method_names=['get']),
        name='api-flags-list'),

)
