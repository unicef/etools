from django.urls import path

from etools.applications.partners.views.agreements_v3 import (
    PMPAgreementDetailUpdateAPIView,
    PMPAgreementListCreateAPIView,
)
from etools.applications.partners.views.interventions_v3 import (
    InterventionActivityCreateView,
    InterventionActivityDetailUpdateView,
    InterventionPDOutputsDetailUpdateView,
    InterventionPDOutputsListCreateView,
    PMPInterventionListCreateView,
    PMPInterventionManagementBudgetRetrieveUpdateView,
    PMPInterventionRetrieveUpdateView,
    PMPInterventionSendToPartnerView,
    PMPInterventionSendToUNICEFView,
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
        name='intervention-pd-output-list',
    ),
    path(
        'interventions/<int:intervention_pk>/pd-outputs/<int:pk>/',
        view=InterventionPDOutputsDetailUpdateView.as_view(),
        name='intervention-pd-output-detail',
    ),
    path(
        'interventions/<int:intervention_pk>/budget/',
        view=PMPInterventionManagementBudgetRetrieveUpdateView.as_view(),
        name='intervention-budget',
    ),
    path(
        'interventions/<int:pk>/send_to_partner/',
        view=PMPInterventionSendToPartnerView.as_view(
            http_method_names=['patch'],
        ),
        name='intervention-send-partner',
    ),
    path(
        'interventions/<int:pk>/send_to_unicef/',
        view=PMPInterventionSendToUNICEFView.as_view(
            http_method_names=['patch'],
        ),
        name='intervention-send-unicef',
    ),
    path(
        'interventions/<int:intervention_pk>/pd-outputs/<int:output_pk>/activities/',
        view=InterventionActivityCreateView.as_view(),
        name='intervention-activity-list',
    ),
    path(
        'interventions/<int:intervention_pk>/pd-outputs/<int:output_pk>/activities/<int:pk>/',
        view=InterventionActivityDetailUpdateView.as_view(),
        name='intervention-activity-detail',
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
