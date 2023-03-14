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
    PMPInterventionAttachmentListCreateView,
    PMPInterventionAttachmentUpdateDeleteView,
    PMPInterventionDeleteView,
    PMPInterventionIndicatorsListView,
    PMPInterventionIndicatorsUpdateView,
    PMPInterventionListCreateView,
    PMPInterventionManagementBudgetRetrieveUpdateView,
    PMPInterventionPDFView,
    PMPInterventionReportingRequirementView,
    PMPInterventionRetrieveResultsStructure,
    PMPInterventionRetrieveUpdateView,
    PMPInterventionSupplyItemListCreateView,
    PMPInterventionSupplyItemRetrieveUpdateView,
    PMPInterventionSupplyItemUploadView,
    PMPInterventionXLSView,
    PMPOfficerReviewDetailView,
    PMPOfficerReviewListView,
    PMPReviewDetailView,
    PMPReviewNotifyView,
    PMPReviewView,
)
from etools.applications.partners.views.interventions_v3_actions import (
    PMPAmendedInterventionMerge,
    PMPInterventionAcceptOnBehalfOfPartner,
    PMPInterventionAcceptView,
    PMPInterventionCancelView,
    PMPInterventionRejectReviewView,
    PMPInterventionReviewView,
    PMPInterventionSendBackViewReview,
    PMPInterventionSendToPartnerView,
    PMPInterventionSendToUNICEFView,
    PMPInterventionSignatureView,
    PMPInterventionSuspendView,
    PMPInterventionTerminateView,
    PMPInterventionUnlockView,
    PMPInterventionUnsuspendView,
)
from etools.applications.partners.views.partner_organization_v3 import (
    PMPPartnerOrganizationListAPIView,
    PMPPartnerStaffMemberListAPIVIew,
)
from etools.applications.partners.views.v3 import PMPDropdownsListApiView

app_name = 'partners'
urlpatterns = [
    path(
        'partners/',
        view=PMPPartnerOrganizationListAPIView.as_view(
            http_method_names=['get'],
        ),
        name='partner-list',
    ),
    path(
        'partners/<int:partner_pk>/staff-members/',
        view=PMPPartnerStaffMemberListAPIVIew.as_view(
            http_method_names=['get'],
        ),
        name='partner-staff-members-list',
    ),
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
        'interventions/<int:pk>/results-structure/',
        view=PMPInterventionRetrieveResultsStructure.as_view(
            http_method_names=['get'],
        ),
        name='intervention-detail-results-structure',
    ),
    path(
        'interventions/<int:pk>/pdf/',
        view=PMPInterventionPDFView.as_view(http_method_names=['get']),
        name='intervention-detail-pdf',
    ),
    path(
        'interventions/<int:pk>/xls/',
        view=PMPInterventionXLSView.as_view(http_method_names=['get']),
        name='intervention-detail-xls',
    ),
    path(
        'interventions/<int:pk>/delete/',
        view=PMPInterventionDeleteView.as_view(http_method_names=['delete']),
        name='intervention-delete',
    ),
    path(
        'interventions/<int:pk>/accept/',
        view=PMPInterventionAcceptView.as_view(http_method_names=['patch']),
        name='intervention-accept',
    ),
    path(
        'interventions/<int:pk>/accept_on_behalf_of_partner/',
        view=PMPInterventionAcceptOnBehalfOfPartner.as_view(http_method_names=['patch']),
        name='intervention-accept-behalf-of-partner',
    ),
    path(
        'interventions/<int:pk>/review/',
        view=PMPInterventionReviewView.as_view(http_method_names=['patch']),
        name='intervention-review',
    ),
    path(
        'interventions/<int:pk>/reject_review/',
        view=PMPInterventionRejectReviewView.as_view(
            http_method_names=['patch'],
        ),
        name='intervention-reject-review',
    ),
    path(
        'interventions/<int:pk>/send_back_review/',
        view=PMPInterventionSendBackViewReview.as_view(
            http_method_names=['patch'],
        ),
        name='intervention-send-back-review',
    ),
    path(
        'interventions/<int:pk>/cancel/',
        view=PMPInterventionCancelView.as_view(http_method_names=['patch']),
        name='intervention-cancel',
    ),
    path(
        'interventions/<int:pk>/terminate/',
        view=PMPInterventionTerminateView.as_view(http_method_names=['patch']),
        name='intervention-terminate',
    ),
    path(
        'interventions/<int:pk>/suspend/',
        view=PMPInterventionSuspendView.as_view(http_method_names=['patch']),
        name='intervention-suspend',
    ),
    path(
        'interventions/<int:pk>/unsuspend/',
        view=PMPInterventionUnsuspendView.as_view(http_method_names=['patch']),
        name='intervention-unsuspend',
    ),
    path(
        'interventions/<int:pk>/sign/',
        view=PMPInterventionSignatureView.as_view(http_method_names=['patch']),
        name='intervention-signature',
    ),
    path(
        'interventions/<int:pk>/unlock/',
        view=PMPInterventionUnlockView.as_view(http_method_names=['patch']),
        name='intervention-unlock',
    ),
    path(
        'interventions/<int:pk>/amendment_merge/',
        view=PMPAmendedInterventionMerge.as_view(http_method_names=['patch']),
        name='intervention-amendment-merge',
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
        'interventions/<int:intervention_pk>/attachments/',
        view=PMPInterventionAttachmentListCreateView.as_view(http_method_names=['get', 'post']),
        name='intervention-attachment-list',
    ),
    path(
        'interventions/<int:intervention_pk>/attachments/<int:pk>/',
        view=PMPInterventionAttachmentUpdateDeleteView.as_view(http_method_names=['delete', 'patch']),
        name='intervention-attachments-update',
    ),
    path(
        'interventions/<int:intervention_pk>/supply/',
        view=PMPInterventionSupplyItemListCreateView.as_view(),
        name='intervention-supply-item',
    ),
    path(
        'interventions/<int:intervention_pk>/supply/upload/',
        view=PMPInterventionSupplyItemUploadView.as_view(),
        name='intervention-supply-item-upload',
    ),
    path(
        'interventions/<int:intervention_pk>/supply/<int:pk>/',
        view=PMPInterventionSupplyItemRetrieveUpdateView.as_view(),
        name='intervention-supply-item-detail',
    ),
    path(
        'interventions/<int:intervention_pk>/reviews/',
        view=PMPReviewView.as_view(),
        name='intervention-reviews',
    ),
    path(
        'interventions/<int:intervention_pk>/reviews/<int:pk>/',
        view=PMPReviewDetailView.as_view(),
        name='intervention-reviews-detail',
    ),
    path(
        'interventions/<int:intervention_pk>/reviews/<int:pk>/notify/',
        view=PMPReviewNotifyView.as_view(),
        name='intervention-reviews-notify',
    ),
    path(
        'interventions/<int:intervention_pk>/reviews/<int:review_pk>/officers-reviews/',
        view=PMPOfficerReviewListView.as_view(),
        name='intervention-officers-review-list',
    ),
    path(
        'interventions/<int:intervention_pk>/reviews/<int:review_pk>/officers-reviews/<int:user_pk>/',
        view=PMPOfficerReviewDetailView.as_view(),
        name='intervention-officers-review-detail',
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
        'interventions/applied-indicators/<int:pk>/',
        view=PMPInterventionIndicatorsUpdateView.as_view(
            http_method_names=['get', 'patch', 'delete'],
        ),
        name='intervention-indicators-update',
    ),
    path(
        'interventions/<int:intervention_pk>/reporting-requirements/<str:report_type>/',
        view=PMPInterventionReportingRequirementView.as_view(
            http_method_names=['get', 'post', 'patch', 'delete']
        ),
        name='intervention-reporting-requirements',
    ),
    path(
        'interventions/lower-results/<int:lower_result_pk>/indicators/',
        view=PMPInterventionIndicatorsListView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='intervention-indicators-list',
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
