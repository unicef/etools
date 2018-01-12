from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from hact.views import GraphHactView, HactHistoryAPIView

urlpatterns = (
    url(r'^history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    url(r'^global_history/$', view=GraphHactView.as_view(), name='global-hact-history'),

)
