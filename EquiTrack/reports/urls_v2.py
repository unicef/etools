from django.conf.urls import url

from reports.views.v2 import (
    AppliedIndicatorListAPIView,
    DisaggregationListCreateView,
    DisaggregationRetrieveUpdateView,
    LowerResultsListAPIView,
    LowerResultsDeleteView,
    OutputListAPIView,
    OutputDetailAPIView,
    ResultIndicatorListAPIView,
    ExportAppliedIndicatorLocationListView
)
from reports.views.v1 import CountryProgrammeListView, CountryProgrammeRetrieveView


urlpatterns = (
    url(r'^reports/results/$', view=OutputListAPIView.as_view(), name='report-result-list'),
    url(r'^reports/applied-indicators/$',
        view=AppliedIndicatorListAPIView.as_view(http_method_names=['get']),
        name='applied-indicator'),
    url(r'^reports/applied-indicators/intervention/$',
        view=ExportAppliedIndicatorLocationListView.as_view(http_method_names=['get']),
        name='intervention-applied-indicator'),
    url(r'^reports/lower_results/$',
        view=LowerResultsListAPIView.as_view(http_method_names=['get']),
        name='lower-results'),
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
        name='disaggregation-list-create'),
    url(r'reports/disaggregations/(?P<pk>\d+)/$', view=DisaggregationRetrieveUpdateView.as_view(),
        name='disaggregation-retrieve-update'),
)
