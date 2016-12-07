from django.conf.urls import url

from reports.views.v2 import ResultListAPIView


urlpatterns = (
    url(r'^reports/results/$', view=ResultListAPIView.as_view(), name='report-result-list'),
)
