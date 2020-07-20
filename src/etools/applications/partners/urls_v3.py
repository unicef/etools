from django.urls import path

from etools.applications.partners.views.agreements_v3 import (
    PMPAgreementDetailUpdateAPIView,
    PMPAgreementListCreateAPIView,
)
from etools.applications.partners.views.interventions_v3 import (
    PMPInterventionListCreateView,
    PMPInterventionRetrieveUpdateView, InterventionPDOutputsListCreateView,
)

app_name = 'partners'
urlpatterns = [
    path(
        'interventions/',
        view=PMPInterventionListCreateView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='intervention-list',
    ),
    path(
        'interventions/<int:pk>/',
        view=PMPInterventionRetrieveUpdateView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='intervention-detail',
    ),
    path(
        'interventions/<int:intervention_pk>/pd-outputs/',
        view=InterventionPDOutputsListCreateView.as_view(),
        name='intervention-pd-outputs',
    ),
    path(
        'agreements/',
        view=PMPAgreementListCreateAPIView.as_view(),
        name='agreement-list',
    ),
    path(
        'agreements/<int:pk>/',
        view=PMPAgreementDetailUpdateAPIView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='agreement-detail',
    ),
]
