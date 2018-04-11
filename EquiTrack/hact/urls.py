
from django.conf.urls import url

from hact.views import GraphHactView, HactHistoryAPIView

urlpatterns = (
    url(r'^history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    url(r'^graph/(?P<year>[0-9]+)/$$', view=GraphHactView.as_view(), name='hact-graph'),

)
