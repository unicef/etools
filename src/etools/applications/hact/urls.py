
from django.conf.urls import url

from etools.applications.hact.views import GraphHactExportView, GraphHactView, HactHistoryAPIView

app_name = 'hact'
urlpatterns = (
    url(r'^history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    url(r'^graph/(?P<year>[0-9]+)/$', view=GraphHactView.as_view(), name='hact-graph'),
    url(r'^graph/(?P<year>[0-9]+)/export/$', view=GraphHactExportView.as_view(), name='hact-graph-export'),
)
