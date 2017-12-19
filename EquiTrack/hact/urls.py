from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from hact.views import GlobalHactView, HactHistoryAPIView

urlpatterns = (
    url(r'^hact_history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    url(r'^global_hact_history/$', view=GlobalHactView.as_view(), name='global-hact-history'),

)
