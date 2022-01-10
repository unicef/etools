from django.urls import include, re_path

from rest_framework import routers

from etools.applications.reports.views.v1 import CountryProgrammeListView, CountryProgrammeRetrieveView, SectionViewSet
from etools.applications.reports.views.v2 import (
    AppliedIndicatorListAPIView,
    AppliedIndicatorLocationExportView,
    ClusterListAPIView,
    DisaggregationListCreateView,
    DisaggregationRetrieveUpdateView,
    LowerResultsDeleteView,
    LowerResultsListAPIView,
    OutputDetailAPIView,
    OutputListAPIView,
    ResultFrameworkView,
    ResultIndicatorListAPIView,
    SpecialReportingRequirementListCreateView,
    SpecialReportingRequirementRetrieveUpdateDestroyView,
)

api = routers.DefaultRouter()
api.register(r'sections', SectionViewSet, basename='sections')

app_name = 'reports'
urlpatterns = (
    re_path(r'^results/$', view=OutputListAPIView.as_view(), name='report-result-list'),
    re_path(r'^applied-indicators/$',
            view=AppliedIndicatorListAPIView.as_view(http_method_names=['get']),
            name='applied-indicator'),
    re_path(r'^applied-indicators/intervention/$',
            view=AppliedIndicatorLocationExportView.as_view(http_method_names=['get']),
            name='intervention-applied-indicator'),
    re_path(r'^clusters/$',
            view=ClusterListAPIView.as_view(http_method_names=['get']),
            name='cluster'),
    re_path(r'^lower_results/$',
            view=LowerResultsListAPIView.as_view(http_method_names=['get']),
            name='lower-results'),
    re_path(r'^lower_results/(?P<pk>\d+)/$',
            view=LowerResultsDeleteView.as_view(http_method_names=['delete']),
            name='lower-results-del'),
    re_path(r'^results/(?P<pk>\d+)/$', view=OutputDetailAPIView.as_view(), name='report-result-detail'),
    re_path(r'^countryprogramme/$', view=CountryProgrammeListView.as_view(),
            name='country-programme-list'),
    re_path(r'^countryprogramme/(?P<pk>\d+)/$',
            view=CountryProgrammeRetrieveView.as_view(http_method_names=['get']), name='country-programme-retrieve'),
    re_path(r'^results/(?P<pk>\d+)/indicators/$',
            view=ResultIndicatorListAPIView.as_view(http_method_names=['get']),
            name='result-indicator-list'),
    re_path(r'disaggregations/$', view=DisaggregationListCreateView.as_view(),
            name='disaggregation-list-create'),
    re_path(r'disaggregations/(?P<pk>\d+)/$', view=DisaggregationRetrieveUpdateView.as_view(),
            name='disaggregation-retrieve-update'),
    re_path(
        r'interventions/(?P<intervention_pk>\d+)/special-reporting-requirements/$',
        view=SpecialReportingRequirementListCreateView.as_view(),
        name="interventions-special-reporting-requirements",
    ),
    re_path(
        r'interventions/special-reporting-requirements/(?P<pk>\d+)/$',
        view=SpecialReportingRequirementRetrieveUpdateDestroyView.as_view(),
        name="interventions-special-reporting-requirements-update",
    ),
    re_path(
        r'interventions/results/(?P<pk>\d+)/$',
        view=ResultFrameworkView.as_view(),
        name="interventions-results-framework",
    ),
    re_path(r'^', include(api.urls))
)
