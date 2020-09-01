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
    InterventionRiskDeleteView,
    PMPInterventionListCreateView,
    PMPInterventionManagementBudgetRetrieveUpdateView,
    PMPInterventionRetrieveUpdateView,
    PMPInterventionSupplyItemListCreateView,
    PMPInterventionSupplyItemRetrieveUpdateView,
)
from etools.applications.partners.views.interventions_v3_actions import (
    PMPInterventionAcceptReviewView,
    PMPInterventionAcceptView,
    PMPInterventionSendToPartnerView,
    PMPInterventionSendToUNICEFView,
    PMPInterventionUnlockView,
)
from etools.applications.partners.views.v3 import PMPDropdownsListApiView

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
        'interventions/<int:pk>/accept/',
        view=PMPInterventionAcceptView.as_view(),
        name='intervention-accept',
    ),
    path(
        'interventions/<int:pk>/accept_review/',
        view=PMPInterventionAcceptReviewView.as_view(),
        name='intervention-accept-review',
    ),
    path(
        'interventions/<int:pk>/unlock/',
        view=PMPInterventionUnlockView.as_view(),
        name='intervention-unlock',
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
        'interventions/<int:intervention_pk>/supply/',
        view=PMPInterventionSupplyItemListCreateView.as_view(),
        name='intervention-supply-item',
    ),
    path(
        'interventions/<int:intervention_pk>/supply/<int:pk>/',
        view=PMPInterventionSupplyItemRetrieveUpdateView.as_view(),
        name='intervention-supply-item-detail',
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
        'interventions/<int:intervention_pk>/risks/<int:pk>/',
        view=InterventionRiskDeleteView.as_view(http_method_names=['delete']),
        name='intervention-risk-delete',
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
    path('dropdowns/dynamic/', view=PMPDropdownsListApiView.as_view(), name='dropdown-dynamic-list'),
]
