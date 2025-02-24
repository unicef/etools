from django.urls import path

from etools.applications.governments.views.exports import (
    GDDLocationsExportView,
    GDDPDFView,
    GDDResultsExportView,
    GDDXLSView,
)
from etools.applications.governments.views.gdd import (
    GDDActivityCreateView,
    GDDActivityDetailUpdateView,
    GDDAmendmentDeleteView,
    GDDAmendmentListAPIView,
    GDDAttachmentListCreateView,
    GDDAttachmentUpdateDeleteView,
    GDDFRsView,
    GDDKeyInterventionDetailUpdateView,
    GDDKeyInterventionListCreateView,
    GDDListCreateView,
    GDDReportingRequirementView,
    GDDResultLinkListCreateView,
    GDDResultLinkUpdateView,
    GDDRetrieveResultsStructure,
    GDDRetrieveUpdateView,
    GDDRiskDeleteView,
    GDDSpecialReportingRequirementListCreateView,
    GDDSpecialReportingRequirementUpdateDestroyView,
    GDDSupplyItemListCreateView,
    GDDSupplyItemRetrieveUpdateView,
    GDDSupplyItemUploadView,
    GDDSyncResultsStructure,
)
from etools.applications.governments.views.gdd_actions import (
    GDDAcceptOnBehalfOfPartner,
    GDDAcceptView,
    GDDCancelView,
    GDDRejectReviewView,
    GDDReviewView,
    GDDSendBackViewReview,
    GDDSendToPartnerView,
    GDDSendToUNICEFView,
    GDDSignatureView,
    GDDSuspendView,
    GDDTerminateView,
    GDDUnlockView,
    GDDUnsuspendView,
    PMPAmendedGDDMerge,
)
from etools.applications.governments.views.government import (
    EWPActivityListView,
    EWPKeyInterventionListView,
    EWPOutputListView,
    GovernmentEWPListView,
    GovernmentOrganizationListAPIView,
    GovernmentStaffMemberListAPIVIew,
)
from etools.applications.governments.views.prp import PRPGDDFileView, PRPGDDListAPIView
from etools.applications.governments.views.review import (
    GDDOfficerReviewDetailView,
    GDDOfficerReviewListView,
    GDDReviewDetailPDFView,
    GDDReviewDetailView,
    GDDReviewNotifyAuthorizedOfficerView,
    GDDReviewNotifyView,
)

app_name = 'governments'


urlpatterns = [
    path(
        'governments/',
        view=GovernmentOrganizationListAPIView.as_view(
            http_method_names=['get'],
        ),
        name='government-list',
    ),
    path(
        'governments/<int:partner_pk>/staff-members/',
        view=GovernmentStaffMemberListAPIVIew.as_view(
            http_method_names=['get'],
        ),
        name='government-staff-members-list',
    ),
    path(
        'gdds/',
        view=GDDListCreateView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='gdd-list',
    ),
    path(
        'gdds/<int:pk>/',
        view=GDDRetrieveUpdateView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='gdd-detail',
    ),
    path(
        'gdds/<int:gdd_pk>/reporting-requirements/<str:report_type>/',
        view=GDDReportingRequirementView.as_view(
            http_method_names=['get', 'post', 'patch', 'delete']
        ),
        name='gdd-reporting-requirements',
    ),
    path(
        'gdds/<int:gdd_pk>/special-reporting-requirements/',
        view=GDDSpecialReportingRequirementListCreateView.as_view(
            http_method_names=['get', 'post']
        ),
        name='gdd-special-reporting-requirements-list',
    ),
    path(
        'gdds/<int:gdd_pk>/special-reporting-requirements/<int:pk>/',
        view=GDDSpecialReportingRequirementUpdateDestroyView.as_view(
            http_method_names=['get', 'patch', 'delete']
        ),
        name='gdd-special-reporting-requirements-detail',
    ),
    path(
        'gdds/<int:pk>/results-structure/',
        view=GDDRetrieveResultsStructure.as_view(
            http_method_names=['get'],
        ),
        name='gdd-detail-results-structure',
    ),
    path(
        'gdds/<int:pk>/sync-results-structure/',
        view=GDDSyncResultsStructure.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='gdd-sync-results-structure',
    ),
    path(
        'gdds/<int:pk>/result-links/',
        view=GDDResultLinkListCreateView.as_view(
            http_method_names=['get', 'post']
        ),
        name='gdd-result-links-list'),
    path(
        'gdds/<int:gdd_pk>/result-links/<int:pk>/',
        view=GDDResultLinkUpdateView.as_view(
            http_method_names=['delete', 'patch']
        ),
        name='gdd-result-links-detail'),
    path(
        'gdds/<int:pk>/key-interventions/',
        view=GDDKeyInterventionListCreateView.as_view(
            http_method_names=['post', 'get']
        ),
        name='gdd-key-intervention-create'),
    path(
        'gdds/<int:gdd_pk>/key-interventions/<int:pk>/',
        view=GDDKeyInterventionDetailUpdateView.as_view(
            http_method_names=['patch', 'get', 'delete']
        ),
        name='gdd-key-intervention-detail'),
    path(
        'gdds/<int:gdd_pk>/key-interventions/<int:key_intervention_pk>/activities/',
        view=GDDActivityCreateView.as_view(
            http_method_names=['post']
        ),
        name='gdd-activity-create'),
    path(
        'gdds/<int:gdd_pk>/key-interventions/<int:key_intervention_pk>/activities/<int:pk>/',
        view=GDDActivityDetailUpdateView.as_view(
            http_method_names=['patch', 'get', 'delete']
        ),
        name='gdd-activity-detail'),
    path(
        'dropdown-options/e-workplans/',
        view=GovernmentEWPListView.as_view(
            http_method_names=['get'],
        ),
        name='e-workplan-list',
    ),
    path(
        'dropdown-options/ewp-outputs/',
        view=EWPOutputListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-output-list',
    ),
    path(
        'dropdown-options/ewp-key-interventions/',
        view=EWPKeyInterventionListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-key-intervention-list',
    ),
    path(
        'dropdown-options/ewp-activities/',
        view=EWPActivityListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-activity-list',
    ),
    path(
        'gdds/<int:gdd_pk>/risks/<int:pk>/',
        view=GDDRiskDeleteView.as_view(http_method_names=['delete']),
        name='intervention-risk-delete',
    ),
] + [
    path(
        'gdds/<int:pk>/accept/',
        view=GDDAcceptView.as_view(http_method_names=['patch']),
        name='gdd-accept',
    ),
    path(
        'gdds/<int:pk>/accept_on_behalf_of_partner/',
        view=GDDAcceptOnBehalfOfPartner.as_view(http_method_names=['patch']),
        name='gdd-accept-behalf-of-partner',
    ),
    path(
        'gdds/<int:pk>/review/',
        view=GDDReviewView.as_view(http_method_names=['patch']),
        name='gdd-review',
    ),
    path(
        'gdds/<int:pk>/reject_review/',
        view=GDDRejectReviewView.as_view(
            http_method_names=['patch'],
        ),
        name='gdd-reject-review',
    ),
    path(
        'gdds/<int:pk>/send_back_review/',
        view=GDDSendBackViewReview.as_view(
            http_method_names=['patch'],
        ),
        name='gdd-send-back-review',
    ),
    path(
        'gdds/<int:pk>/cancel/',
        view=GDDCancelView.as_view(http_method_names=['patch']),
        name='gdd-cancel',
    ),
    path(
        'gdds/<int:pk>/terminate/',
        view=GDDTerminateView.as_view(http_method_names=['patch']),
        name='gdd-terminate',
    ),
    path(
        'gdds/<int:pk>/suspend/',
        view=GDDSuspendView.as_view(http_method_names=['patch']),
        name='gdd-suspend',
    ),
    path(
        'gdds/<int:pk>/unsuspend/',
        view=GDDUnsuspendView.as_view(http_method_names=['patch']),
        name='gdd-unsuspend',
    ),
    path(
        'gdds/<int:pk>/sign/',
        view=GDDSignatureView.as_view(http_method_names=['patch']),
        name='gdd-signature',
    ),
    path(
        'gdds/<int:pk>/unlock/',
        view=GDDUnlockView.as_view(http_method_names=['patch']),
        name='gdd-unlock',
    ),
    path(
        'gdds/<int:pk>/send_to_partner/',
        view=GDDSendToPartnerView.as_view(
            http_method_names=['patch'],
        ),
        name='gdd-send-partner',
    ),
    path(
        'gdds/<int:pk>/send_to_unicef/',
        view=GDDSendToUNICEFView.as_view(
            http_method_names=['patch'],
        ),
        name='gdd-send-unicef',
    ),
    path(
        'gdds/<int:gdd_pk>/amendments/',
        view=GDDAmendmentListAPIView.as_view(http_method_names=['get', 'post']),
        name='gdd-amendments-list'
    ),
    path(
        'gdds/amendments/<int:pk>/',
        view=GDDAmendmentDeleteView.as_view(http_method_names=['delete', ]),
        name='gdd-amendments-del'
    ),
    path(
        'gdds/<int:pk>/amendment_merge/',
        view=PMPAmendedGDDMerge.as_view(http_method_names=['patch']),
        name='gdd-amendment-merge',
    ),
    path(
        'gdds/<int:gdd_pk>/supply/',
        view=GDDSupplyItemListCreateView.as_view(),
        name='gdd-supply-item',
    ),
    path(
        'gdds/<int:gdd_pk>/supply/upload/',
        view=GDDSupplyItemUploadView.as_view(),
        name='gdd-supply-item-upload',
    ),
    path(
        'gdds/<int:gdd_pk>/supply/<int:pk>/',
        view=GDDSupplyItemRetrieveUpdateView.as_view(),
        name='gdd-supply-item-detail',
    ),
] + [
    path(
        'gdds/<int:pk>/reviews/',
        view=GDDReviewView.as_view(http_method_names=['patch']),
        name='gdd-review',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:pk>/',
        view=GDDReviewDetailView.as_view(http_method_names=['patch']),
        name='gdd-reviews-detail',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:pk>/notify/',
        view=GDDReviewNotifyView.as_view(),
        name='gdd-reviews-notify',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:pk>/notify-authorized-officer/',
        view=GDDReviewNotifyAuthorizedOfficerView.as_view(),
        name='gdd-reviews-notify-authorized-officer',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:review_pk>/pdf/',
        view=GDDReviewDetailPDFView.as_view(),
        name='gdd-review-pdf',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:review_pk>/officers-reviews/',
        view=GDDOfficerReviewListView.as_view(),
        name='intervention-officers-review-list',
    ),
    path(
        'gdds/<int:gdd_pk>/reviews/<int:review_pk>/officers-reviews/<int:user_pk>/',
        view=GDDOfficerReviewDetailView.as_view(),
        name='intervention-officers-review-detail',
    ),
    path(
        'gdds/<int:gdd_pk>/attachments/',
        view=GDDAttachmentListCreateView.as_view(http_method_names=['get', 'post']),
        name='intervention-attachment-list',
    ),
    path(
        'gdds/<int:gdd_pk>/attachments/<int:pk>/',
        view=GDDAttachmentUpdateDeleteView.as_view(http_method_names=['delete', 'patch']),
        name='gdd-attachments-update',
    ),
    path(
        'frs/',
        view=GDDFRsView.as_view(http_method_names=['get']),
        name='frs',
    ),

    # ************** EXPORTS ****************************
    path('gdds/results/',
         view=GDDResultsExportView.as_view(http_method_names=['get']),
         name='results-export'),
    path('gdds/locations/',
         view=GDDLocationsExportView.as_view(http_method_names=['get']),
         name='results-export'),
    path(
        'gdds/<int:pk>/pdf/',
        view=GDDPDFView.as_view(http_method_names=['get']),
        name='intervention-detail-pdf',
    ),
    path(
        'gdds/<int:pk>/xls/',
        view=GDDXLSView.as_view(http_method_names=['get']),
        name='intervention-detail-xls',
    ),

    # ************** PRP ********************************
    path(
        'prp-gdds/',
        view=PRPGDDListAPIView.as_view(http_method_names=['get']),
        name='prp-gdd-list'),
    path(
        'prp-get-gpd-document/<int:gdd_pk>/',
        view=PRPGDDFileView.as_view(http_method_names=['get']),
        name='prp-gpd-document-get'),
]
