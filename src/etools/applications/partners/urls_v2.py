from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

from etools.applications.partners.views.agreements_v2 import (AgreementAmendmentDeleteView,
                                                              AgreementAmendmentListAPIView, AgreementDeleteView,
                                                              AgreementDetailAPIView, AgreementListAPIView,)
from etools.applications.partners.views.dashboards import InterventionPartnershipDashView
from etools.applications.partners.views.interventions_v2 import (InterventionAmendmentDeleteView,
                                                                 InterventionAmendmentListAPIView,
                                                                 InterventionAttachmentDeleteView,
                                                                 InterventionDeleteView, InterventionDetailAPIView,
                                                                 InterventionIndicatorListAPIView,
                                                                 InterventionIndicatorsListView,
                                                                 InterventionIndicatorsUpdateView,
                                                                 InterventionListAPIView, InterventionListDashView,
                                                                 InterventionListMapView,
                                                                 InterventionLocationListAPIView,
                                                                 InterventionLowerResultListCreateView,
                                                                 InterventionLowerResultUpdateView,
                                                                 InterventionReportingPeriodDetailView,
                                                                 InterventionReportingPeriodListCreateView,
                                                                 InterventionReportingRequirementView,
                                                                 InterventionResultLinkDeleteView,
                                                                 InterventionResultLinkListCreateView,
                                                                 InterventionResultLinkUpdateView,
                                                                 InterventionResultListAPIView,
                                                                 InterventionSectionLocationLinkListAPIView, )
from etools.applications.partners.views.partner_organization_v2 import (
    PartnerOrganizationAddView,
    PartnerOrganizationAssessmentDeleteView,
    PartnerOrganizationAssessmentListView,
    PartnerOrganizationDeleteView,
    PartnerOrganizationDetailAPIView,
    PartnerOrganizationHactAPIView,
    PartnerOrganizationListAPIView,
    PartnerOrganizationSimpleHactAPIView,
    PartnerStaffMemberListAPIVIew,
    PlannedEngagementAPIView,
    PartnerNotAssuranceCompliant,
    PartnerNotSpotCheckCompliant,
    PartnerNotProgrammaticVisitCompliant,
    PartnerPlannedVisitsDeleteView,
    PartnerWithSpecialAuditCompleted,
    PartnerWithScheduledAuditCompleted,
)
from etools.applications.partners.views.v1 import PCAPDFView
from etools.applications.partners.views.v2 import PMPDropdownsListApiView, PMPStaticDropdownsListAPIView

# http://www.django-rest-framework.org/api-guide/format-suffixes/

app_name = 'partners'
urlpatterns = (

    url(r'^agreements/$', view=AgreementListAPIView.as_view(), name='agreement-list'),
    url(r'^agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(http_method_names=['get', 'patch']),
        name='agreement-detail'),

    url(r'^agreements/delete/(?P<pk>\d+)/$', view=AgreementDeleteView.as_view(http_method_names=['delete']),
        name='agreement-delete'),

    url(r'^agreements/(?P<agr>\d+)/generate_doc/$', PCAPDFView.as_view(), name='pca_pdf'),
    url(r'^agreements/amendments/$',
        view=AgreementAmendmentListAPIView.as_view(),
        name='agreement-amendment-list'),
    url(r'^agreements/amendments/(?P<pk>\d+)/$',
        view=AgreementAmendmentDeleteView.as_view(http_method_names=['delete']),
        name='agreement-amendment-del'),

    url(r'^partners/$',
        view=PartnerOrganizationListAPIView.as_view(http_method_names=['get']),
        name='partner-list'),
    url(r'^partners/not_programmatic_visit/$',
        view=PartnerNotProgrammaticVisitCompliant.as_view(http_method_names=['get']),
        name='partner-list-not-programmatic-visit'),
    url(r'^partners/not_spot_check/$',
        view=PartnerNotSpotCheckCompliant.as_view(http_method_names=['get']),
        name='partner-list-not-spot-check'),
    url(r'^partners/not_assurance/$',
        view=PartnerNotAssuranceCompliant.as_view(http_method_names=['get']),
        name='partner-list-not-assurance'),
    url(r'^partners/special_audit_completed/$',
        view=PartnerWithSpecialAuditCompleted.as_view(http_method_names=['get']),
        name='partner-special-audit-completed'),
    url(r'^partners/scheduled_audit_completed/$',
        view=PartnerWithScheduledAuditCompleted.as_view(http_method_names=['get']),
        name='partner-scheduled-audit-completed'),
    url(
        r'^partners/planned-visits/(?P<pk>\d+)/$',
        view=PartnerPlannedVisitsDeleteView.as_view(http_method_names=['delete', ]),
        name='partner-planned-visits-del'
    ),

    url(r'^partners/hact/$',
        view=PartnerOrganizationHactAPIView.as_view(http_method_names=['get', ]),
        name='partner-hact'),
    url(r'^partners/hact/simple/$',
        view=PartnerOrganizationSimpleHactAPIView.as_view(http_method_names=['get', ]),
        name='partner-hact-simple'),
    url(r'^partners/engagements/$',
        view=PlannedEngagementAPIView.as_view(http_method_names=['get', ]),
        name='partner-engagements'),
    url(r'^partners/(?P<pk>\d+)/$',
        view=PartnerOrganizationDetailAPIView.as_view(http_method_names=['get', 'patch']),
        name='partner-detail'),
    url(r'^partners/delete/(?P<pk>\d+)/$',
        view=PartnerOrganizationDeleteView.as_view(http_method_names=['delete']),
        name='partner-delete'),
    url(r'^partners/assessments/$',
        view=PartnerOrganizationAssessmentListView.as_view(http_method_names=['get', ]),
        name='partner-assessment'),
    url(r'^partners/assessments/(?P<pk>\d+)/$',
        view=PartnerOrganizationAssessmentDeleteView.as_view(http_method_names=['delete', ]),
        name='partner-assessment-del'),
    url(r'^partners/add/$', view=PartnerOrganizationAddView.as_view(http_method_names=['post']), name='partner-add'),

    url(r'^partners/(?P<partner_pk>\d+)/staff-members/$',
        view=PartnerStaffMemberListAPIVIew.as_view(http_method_names=['get']),
        name='partner-staff-members-list'),

    url(r'^interventions/$',
        view=InterventionListAPIView.as_view(http_method_names=['get', 'post']),
        name='intervention-list'),

    url(r'^interventions/result-links/(?P<result_link_pk>\d+)/lower-results/$',
        view=InterventionLowerResultListCreateView.as_view(http_method_names=['get', 'post']),
        name='intervention-lower-results-list'),

    url(r'^interventions/(?P<intervention_pk>\d+)/result-links/$',
        view=InterventionResultLinkListCreateView.as_view(http_method_names=['get', 'post']),
        name='intervention-result-links-list'),

    url(r'^interventions/result-links/(?P<pk>\d+)/$',
        view=InterventionResultLinkUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
        name='intervention-result-links-update'),


    url(r'^interventions/lower-results/(?P<pk>\d+)/$',
        view=InterventionLowerResultUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
        name='intervention-lower-results-update'),

    url(r'^interventions/lower-results/(?P<lower_result_pk>\d+)/indicators/$',
        view=InterventionIndicatorsListView.as_view(http_method_names=['get', 'post']),
        name='intervention-indicators-list'),

    url(r'^interventions/applied-indicators/(?P<pk>\d+)/$',
        view=InterventionIndicatorsUpdateView.as_view(http_method_names=['get', 'patch', 'delete']),
        name='intervention-indicators-update'),

    url(r'^interventions/dash/$',
        view=InterventionListDashView.as_view(http_method_names=['get', 'post']),
        name='intervention-list-dash'),

    url(r'^interventions/(?P<pk>\d+)/$',
        view=InterventionDetailAPIView.as_view(http_method_names=['get', 'patch']),
        name='intervention-detail'),
    url(r'^interventions/delete/(?P<pk>\d+)/$',
        view=InterventionDeleteView.as_view(http_method_names=['delete']),
        name='intervention-delete'),

    url(r'^interventions/attachments/(?P<pk>\d+)/$',
        view=InterventionAttachmentDeleteView.as_view(http_method_names=['delete', ]),
        name='intervention-attachments-del'),
    url(r'^interventions/indicators/$',
        view=InterventionIndicatorListAPIView.as_view(http_method_names=['get', ]),
        name='intervention-indicators'),
    url(r'^interventions/results/$',
        view=InterventionResultListAPIView.as_view(http_method_names=['get', ]),
        name='intervention-results'),
    url(r'^interventions/results/(?P<pk>\d+)/$',
        view=InterventionResultLinkDeleteView.as_view(http_method_names=['delete', ]),
        name='intervention-results-del'),
    url(r'^interventions/amendments/$',
        view=InterventionAmendmentListAPIView.as_view(http_method_names=['get']),
        name='intervention-amendments'),
    url(r'^interventions/(?P<intervention_pk>\d+)/amendments/$',
        view=InterventionAmendmentListAPIView.as_view(http_method_names=['get', 'post']),
        name='intervention-amendments-add'),
    url(r'^interventions/amendments/(?P<pk>\d+)/$',
        view=InterventionAmendmentDeleteView.as_view(http_method_names=['delete', ]),
        name='intervention-amendments-del'),
    url(r'^interventions/locations/$',
        view=InterventionLocationListAPIView.as_view(http_method_names=['get', ]),
        name='intervention-locations-list'),
    url(r'^interventions/sector-locations/$',
        view=InterventionSectionLocationLinkListAPIView.as_view(http_method_names=['get', ]),
        name='intervention-sector-locations'),
    url(r'^interventions/map/$',
        view=InterventionListMapView.as_view(http_method_names=['get', ]),
        name='intervention-map'),
    url(r'^interventions/partnership-dash/$',
        view=InterventionPartnershipDashView.as_view(http_method_names=['get', ]),
        name='interventions-partnership-dash'),

    url(r'^interventions/(?P<intervention_pk>\d+)/reporting-periods/$',
        view=InterventionReportingPeriodListCreateView.as_view(http_method_names=['get', 'post']),
        name='intervention-reporting-periods-list'),
    url(r'^interventions/reporting-periods/(?P<pk>\d+)/$',
        view=InterventionReportingPeriodDetailView.as_view(http_method_names=['get', 'patch', 'delete']),
        name='intervention-reporting-periods-detail'),
    url(
        r'^interventions/(?P<intervention_pk>\d+)/reporting-requirements/(?P<report_type>\w+)/$',
        view=InterventionReportingRequirementView.as_view(
            http_method_names=['get', 'post', 'patch', 'delete']
        ),
        name='intervention-reporting-requirements'
    ),

    # TODO: figure this out
    # url(r'^partners/interventions/$', view=InterventionsView.as_view()),
    url(r'^dropdowns/static/$',
        view=PMPStaticDropdownsListAPIView.as_view(http_method_names=['get']),
        name='dropdown-static-list'),
    url(r'^dropdowns/pmp/$',
        view=PMPDropdownsListApiView.as_view(http_method_names=['get']), name='dropdown-pmp-list'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
