from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import url

from environment.views import ActiveFlagAPIView

urlpatterns = (
    url(r'^flags/$',
        view=ActiveFlagAPIView.as_view(http_method_names=['get']),
        name='api-flags-list'),

)
