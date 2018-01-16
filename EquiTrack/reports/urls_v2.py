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
)
from reports.views.v1 import CountryProgrammeListView, CountryProgrammeRetrieveView


urlpatterns = (
    url(r'^results/$', view=OutputListAPIView.as_view(), name='report-result-list'),
    url(r'^applied-indicators/$',
        view=AppliedIndicatorListAPIView.as_view(http_method_names=['get']),
        name='applied-indicator'),
    url(r'^lower_results/$',
        view=LowerResultsListAPIView.as_view(http_method_names=['get']),
        name='lower-results'),
    url(r'^lower_results/(?P<pk>\d+)/$',
        view=LowerResultsDeleteView.as_view(http_method_names=['delete']),
        name='lower-results-del'),
    url(r'^results/(?P<pk>\d+)/$', view=OutputDetailAPIView.as_view(), name='report-result-detail'),
    url(r'^countryprogramme/$', view=CountryProgrammeListView.as_view(),
        name='country-programme-list'),
    url(r'^countryprogramme/(?P<pk>\d+)/$',
        view=CountryProgrammeRetrieveView.as_view(http_method_names=['get']), name='country-programme-retrieve'),
    url(r'^results/(?P<pk>\d+)/indicators/$',
        view=ResultIndicatorListAPIView.as_view(http_method_names=['get']),
        name='result-indicator-list'),
    url(r'disaggregations/$', view=DisaggregationListCreateView.as_view(),
        name='disaggregation-list-create'),
    url(r'disaggregations/(?P<pk>\d+)/$', view=DisaggregationRetrieveUpdateView.as_view(),
        name='disaggregation-retrieve-update'),
)
