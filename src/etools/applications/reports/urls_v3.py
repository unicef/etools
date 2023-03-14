from django.urls import path

from etools.applications.reports.views.v3 import (
    PMPResultFrameworkView,
    PMPSpecialReportingRequirementListCreateView,
    PMPSpecialReportingRequirementRetrieveUpdateDestroyView,
)

app_name = 'reports'
urlpatterns = [
    path(
        'interventions/<int:intervention_pk>/special-reporting-requirements/',
        view=PMPSpecialReportingRequirementListCreateView.as_view(),
        name="interventions-special-reporting-requirements",
    ),
    path(
        'interventions/<int:intervention_pk>/special-reporting-requirements/<int:pk>/',
        view=PMPSpecialReportingRequirementRetrieveUpdateDestroyView.as_view(),
        name="interventions-special-reporting-requirements-update",
    ),
    path(
        'interventions/results/<int:pk>/',
        view=PMPResultFrameworkView.as_view(),
        name="interventions-results-framework"
    )
]
