from django.conf.urls import url

from reports.views.v2 import (
    ResultListAPIView,
    ResultDetailAPIView,
)

urlpatterns = (
    url(r'^reports/results/$', view=ResultListAPIView.as_view(), name='report-result-list'),
    url(r'^reports/results/(?P<pk>\d+)/$', view=ResultDetailAPIView.as_view(), name='report-result-detail'),
)
