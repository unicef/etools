from django.conf.urls import url

from reports.views.v2 import OutputListAPIView, OutputDetailAPIView, ResultIndicatorListAPIView, \
    LowerResultsDeleteView, DisaggregationListCreateView
from reports.views.v1 import CountryProgrammeListView, CountryProgrammeRetrieveView


urlpatterns = (
    url(r'^reports/results/$', view=OutputListAPIView.as_view(), name='report-result-list'),
    url(r'^reports/lower_results/(?P<pk>\d+)/$',
        view=LowerResultsDeleteView.as_view(http_method_names=['delete']),
        name='lower-results-del'),
    url(r'^reports/results/(?P<pk>\d+)/$', view=OutputDetailAPIView.as_view(), name='report-result-detail'),
    url(r'^reports/countryprogramme/$', view=CountryProgrammeListView.as_view(),
        name='country-programme-list'),
    url(r'^reports/countryprogramme/(?P<pk>\d+)/$',
        view=CountryProgrammeRetrieveView.as_view(http_method_names=['get']), name='country-programme-retrieve'),
    url(r'^reports/results/(?P<pk>\d+)/indicators/$',
        view=ResultIndicatorListAPIView.as_view(http_method_names=['get']),
        name='result-indicator-list'),
    url(r'reports/disaggregations/$', view=DisaggregationListCreateView.as_view(),
        name='disaggregation-list'),
)
