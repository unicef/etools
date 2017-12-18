from django.conf.urls import url
from hact.views import HactHistoryAPIView, GlobalHactView

urlpatterns = (
    url(r'^hact_history/$', view=HactHistoryAPIView.as_view(http_method_names=['get', ]), name='hact-history'),
    url(r'^global_hact_history/$', view=GlobalHactView.as_view(), name='global-hact-history'),

)