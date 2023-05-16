from django.urls import re_path

from rest_framework.urlpatterns import format_suffix_patterns

from etools.applications.partners.views.agreements_v2 import (
    AgreementAmendmentDeleteView,
    AgreementAmendmentListAPIView,
    AgreementDeleteView,
    AgreementDetailAPIView,
    AgreementListAPIView,
)
from etools.applications.partners.views.dashboards import InterventionPartnershipDashView
from etools.applications.partners.views.interventions_v2 import (
    InterventionAmendmentDeleteView,
    InterventionAmendmentListAPIView,
    InterventionAttachmentListCreateView,
    InterventionAttachmentUpdateDeleteView,
    InterventionDeleteView,
    InterventionDetailAPIView,
    InterventionIndicatorListAPIView,
    InterventionIndicatorsListView,
    InterventionIndicatorsUpdateView,
    InterventionListAPIView,
    InterventionListDashView,
    InterventionListMapView,
    InterventionLocationListAPIView,
    InterventionLowerResultListCreateView,
    InterventionLowerResultUpdateView,
    InterventionPlannedVisitsDeleteView,
    InterventionRamIndicatorsView,
    InterventionReportingPeriodDetailView,
    InterventionReportingPeriodListCreateView,
    InterventionReportingRequirementView,
    InterventionResultLinkListCreateView,
    InterventionResultLinkUpdateView,
    InterventionResultListAPIView,
    InterventionWithAppliedIndicatorsView,
)
from etools.applications.partners.views.partner_organization_v2 import (
    PartnerNotAssuranceCompliant,
    PartnerNotProgrammaticVisitCompliant,
    PartnerNotSpotCheckCompliant,
    PartnerOrganizationAddView,
    PartnerOrganizationAssessmentListCreateView,
    PartnerOrganizationAssessmentUpdateDeleteView,
    PartnerOrganizationDashboardAPIView,
    PartnerOrganizationDeleteView,
    PartnerOrganizationDetailAPIView,
    PartnerOrganizationHactAPIView,
    PartnerOrganizationListAPIView,
    PartnerOrganizationSimpleHactAPIView,
    PartnerPlannedVisitsDeleteView,
    PartnerWithScheduledAuditCompleted,
    PartnerWithSpecialAuditCompleted,
    PlannedEngagementAPIView,
)
from etools.applications.partners.views.v1 import PCAPDFView
from etools.applications.partners.views.v2 import PMPDropdownsListApiView, PMPStaticDropdownsListAPIView

# http://www.django-rest-framework.org/api-guide/format-suffixes/

app_name = 'partners'
urlpatterns = (

    re_path(r'^agreements/$', view=AgreementListAPIView.as_view(), name='agreement-list'),
    re_path(r'^agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(http_method_names=['get', 'patch']),
            name='agreement-detail'),

    re_path(r'^agreements/delete/(?P<pk>\d+)/$', view=AgreementDeleteView.as_view(http_method_names=['delete']),
            name='agreement-delete'),

    re_path(r'^agreements/(?P<agr>\d+)/generate_doc/$', PCAPDFView.as_view(), name='pca_pdf'),
    re_path(r'^agreements/amendments/$',
            view=AgreementAmendmentListAPIView.as_view(),
            name='agreement-amendment-list'),
    re_path(r'^agreements/amendments/(?P<pk>\d+)/$',
            view=AgreementAmendmentDeleteView.as_view(http_method_names=['delete']),
            name='agreement-amendment-del'),

    re_path(r'^partners/$',
            view=PartnerOrganizationListAPIView.as_view(http_method_names=['get']),
            name='partner-list'),
    re_path(r'^partners/not_programmatic_visit/$',
            view=PartnerNotProgrammaticVisitCompliant.as_view(http_method_names=['get']),
            name='partner-list-not-programmatic-visit'),
    re_path(r'^partners/not_spot_check/$',
            view=PartnerNotSpotCheckCompliant.as_view(http_method_names=['get']),
            name='partner-list-not-spot-check'),
    re_path(r'^partners/not_assurance/$',
            view=PartnerNotAssuranceCompliant.as_view(http_method_names=['get']),
            name='partner-list-not-assurance'),
    re_path(r'^partners/special_audit_completed/$',
            view=PartnerWithSpecialAuditCompleted.as_view(http_method_names=['get']),
            name='partner-special-audit-completed'),
    re_path(r'^partners/scheduled_audit_completed/$',
            view=PartnerWithScheduledAuditCompleted.as_view(http_method_names=['get']),
            name='partner-scheduled-audit-completed'),
    re_path(
        r'^partners/planned-visits/(?P<pk>\d+)/$',
        view=PartnerPlannedVisitsDeleteView.as_view(http_method_names=['delete', ]),
        name='partner-planned-visits-del'
    ),

    re_path(r'^partners/hact/$',
            view=PartnerOrganizationHactAPIView.as_view(http_method_names=['get', ]),
            name='partner-hact'),
    re_path(r'^partners/hact/simple/$',
            view=PartnerOrganizationSimpleHactAPIView.as_view(http_method_names=['get', ]),
            name='partner-hact-simple'),
    re_path(r'^partners/dashboard/$',
            view=PartnerOrganizationDashboardAPIView.as_view(http_method_names=['get', ]),
            name='partner-dashboard'),
    re_path(r'^partners/engagements/$',
            view=PlannedEngagementAPIView.as_view(http_method_names=['get', ]),
            name='partner-engagements'),
    re_path(r'^partners/(?P<pk>\d+)/$',
            view=PartnerOrganizationDetailAPIView.as_view(http_method_names=['get', 'patch']),
            name='partner-detail'),
    re_path(r'^partners/delete/(?P<pk>\d+)/$',
            view=PartnerOrganizationDeleteView.as_view(http_method_names=['delete']),
            name='partner-delete'),
    re_path(r'^partners/assessments/$',
            view=PartnerOrganizationAssessmentListCreateView.as_view(http_method_names=['get', 'post']),
            name='partner-assessment'),
    re_path(r'^partners/assessments/(?P<pk>\d+)/$',
            view=PartnerOrganizationAssessmentUpdateDeleteView.as_view(http_method_names=['delete', 'patch']),
            name='partner-assessment-detail'),
    re_path(r'^partners/add/$', view=PartnerOrganizationAddView.as_view(http_method_names=['post']),
            name='partner-add'),

    # re_path(r'^partners/(?P<partner_pk>\d+)/staff-members/$',
    #         view=PartnerStaffMemberListAPIVIew.as_view(http_method_names=['get']),
    #         name='partner-staff-members-list'),

    re_path(r'^interventions/$',
            view=InterventionListAPIView.as_view(http_method_names=['get', 'post']),
            name='intervention-list'),

    re_path(r'^interventions/applied-indicators/$',
            view=InterventionWithAppliedIndicatorsView.as_view(http_method_names=['get', ]),
            name='intervention-applied-indicators-list'),

    re_path(r'^interventions/result-links/(?P<result_link_pk>\d+)/lower-results/$',
            view=InterventionLowerResultListCreateView.as_view(http_method_names=['get', 'post']),
            name='intervention-lower-results-list'),

    re_path(r'^interventions/(?P<intervention_pk>\d+)/result-links/$',
            view=InterventionResultLinkListCreateView.as_view(http_method_names=['get', 'post']),
            name='intervention-result-links-list'),

    re_path(r'^interventions/result-links/(?P<pk>\d+)/$',
            view=InterventionResultLinkUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
            name='intervention-result-links-update'),


    re_path(r'^interventions/lower-results/(?P<pk>\d+)/$',
            view=InterventionLowerResultUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
            name='intervention-lower-results-update'),

    re_path(r'^interventions/lower-results/(?P<lower_result_pk>\d+)/indicators/$',
            view=InterventionIndicatorsListView.as_view(http_method_names=['get', 'post']),
            name='intervention-indicators-list'),

    re_path(r'^interventions/applied-indicators/(?P<pk>\d+)/$',
            view=InterventionIndicatorsUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
            name='intervention-indicators-update'),

    re_path(r'^interventions/dash/$',
            view=InterventionListDashView.as_view(http_method_names=['get', 'post']),
            name='intervention-list-dash'),

    re_path(r'^interventions/(?P<pk>\d+)/$',
            view=InterventionDetailAPIView.as_view(http_method_names=['get', 'patch']),
            name='intervention-detail'),
    re_path(r'^interventions/delete/(?P<pk>\d+)/$',
            view=InterventionDeleteView.as_view(http_method_names=['delete']),
            name='intervention-delete'),

    re_path(r'^interventions/(?P<intervention_pk>\d+)/attachments/$',
            view=InterventionAttachmentListCreateView.as_view(http_method_names=['get', 'post']),
            name='intervention-attachment-list'),

    re_path(r'^interventions/attachments/(?P<pk>\d+)/$',
            view=InterventionAttachmentUpdateDeleteView.as_view(http_method_names=['delete', 'patch']),
            name='intervention-attachments-update'),

    re_path(r'^interventions/indicators/$',
            view=InterventionIndicatorListAPIView.as_view(http_method_names=['get', ]),
            name='intervention-indicators'),
    re_path(r'^interventions/results/$',
            view=InterventionResultListAPIView.as_view(http_method_names=['get', ]),
            name='intervention-results'),
    re_path(r'^interventions/amendments/$',
            view=InterventionAmendmentListAPIView.as_view(http_method_names=['get']),
            name='intervention-amendments'),
    re_path(r'^interventions/(?P<intervention_pk>\d+)/amendments/$',
            view=InterventionAmendmentListAPIView.as_view(http_method_names=['get', 'post']),
            name='intervention-amendments-add'),
    re_path(r'^interventions/amendments/(?P<pk>\d+)/$',
            view=InterventionAmendmentDeleteView.as_view(http_method_names=['delete', ]),
            name='intervention-amendments-del'),
    re_path(r'^interventions/locations/$',
            view=InterventionLocationListAPIView.as_view(http_method_names=['get', ]),
            name='intervention-locations-list'),
    re_path(r'^interventions/map/$',
            view=InterventionListMapView.as_view(http_method_names=['get', ]),
            name='intervention-map'),
    re_path(r'^interventions/partnership-dash/$',
            view=InterventionPartnershipDashView.as_view(http_method_names=['get', ]),
            name='interventions-partnership-dash'),

    re_path(r'^interventions/(?P<intervention_pk>\d+)/reporting-periods/$',
            view=InterventionReportingPeriodListCreateView.as_view(http_method_names=['get', 'post']),
            name='intervention-reporting-periods-list'),
    re_path(r'^interventions/reporting-periods/(?P<pk>\d+)/$',
            view=InterventionReportingPeriodDetailView.as_view(http_method_names=['get', 'patch', 'delete']),
            name='intervention-reporting-periods-detail'),
    re_path(
        r'^interventions/(?P<intervention_pk>\d+)/reporting-requirements/(?P<report_type>\w+)/$',
        view=InterventionReportingRequirementView.as_view(
            http_method_names=['get', 'post', 'patch', 'delete']
        ),
        name='intervention-reporting-requirements'
    ),
    re_path(
        r'interventions/(?P<intervention_pk>\d+)/output_cp_indicators/(?P<cp_output_pk>\d+)/$',
        view=InterventionRamIndicatorsView.as_view(http_method_names=['get']),
        name="interventions-output-cp-indicators",
    ),
    re_path(
        r'interventions/(?P<intervention_pk>\d+)/planned-visits/(?P<pk>\d+)/$',
        view=InterventionPlannedVisitsDeleteView.as_view(http_method_names=['delete']),
        name="interventions-planned-visits-delete",
    ),

    re_path(r'^dropdowns/static/$',
            view=PMPStaticDropdownsListAPIView.as_view(http_method_names=['get']),
            name='dropdown-static-list'),
    re_path(r'^dropdowns/pmp/$',
            view=PMPDropdownsListApiView.as_view(http_method_names=['get']), name='dropdown-pmp-list'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
