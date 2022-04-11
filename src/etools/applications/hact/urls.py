from django.urls import re_path

from etools.applications.hact.views import GraphHactExportView, GraphHactView, HactHistoryAPIView

app_name = 'hact'
urlpatterns = (
    re_path(r'^history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    re_path(r'^graph/(?P<year>[0-9]+)/$', view=GraphHactView.as_view(), name='hact-graph'),
    re_path(r'^graph/(?P<year>[0-9]+)/export/$', view=GraphHactExportView.as_view(), name='hact-graph-export'),
)
