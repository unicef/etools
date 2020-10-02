from django.urls import path

from etools.applications.reports.views.v3 import PMPSpecialReportingRequirementListCreateView

app_name = 'reports'
urlpatterns = [
    path(
        'interventions/<int:intervention_pk>/special-reporting-requirements/',
        view=PMPSpecialReportingRequirementListCreateView.as_view(),
        name="interventions-special-reporting-requirements",
    ),
]
