from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from .views.v1 import PcaPDFView
from .views.partner_organization_v2 import (
    PartnerOrganizationListAPIView, PartnerOrganizationDetailAPIView, PartnerStaffMemberListAPIVIew,
    PartnerOrganizationHactAPIView, PartnerOrganizationAssessmentDeleteView, PartnerOrganizationAddView,
)
from .views.agreements_v2 import (
    AgreementListAPIView,
    AgreementDetailAPIView,
    AgreementAmendmentDeleteView,
    AgreementAmendmentTypeDeleteView,
)
from views.interventions_v2 import (
    InterventionListAPIView,
    InterventionListDashView,
    InterventionDetailAPIView,
    InterventionBudgetDeleteView,
    InterventionPlannedVisitsDeleteView,
    InterventionAttachmentDeleteView,
    InterventionResultLinkDeleteView,
    InterventionAmendmentDeleteView,
    InterventionSectorLocationLinkDeleteView,
    InterventionListMapView,
)
from views.government import (
    GovernmentInterventionListAPIView,
    GovernmentDetailAPIView,
    GovernmentInterventionResultActivityDeleteView,
    GovernmentInterventionResultDeleteView,
)
from views.v2 import (
    PmpStaticDropdownsListApiView, PMPDropdownsListApiView, PartnershipDashboardAPIView
)


# http://www.django-rest-framework.org/api-guide/format-suffixes/

urlpatterns = (

    url(r'^agreements/$', view=AgreementListAPIView.as_view(), name='agreement-list'),
    url(r'^agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(), name='agreement-detail'),
    url(r'^agreements/(?P<agr>\d+)/pdf', PcaPDFView.as_view(), name='pca_pdf'),
    url(r'^agreements/amendments/(?P<pk>\d+)/$', view=AgreementAmendmentDeleteView.as_view(http_method_names=['delete']), name='agreement-amendment-del'),
    url(r'^agreements/amendments/types/(?P<pk>\d+)/$', view=AgreementAmendmentTypeDeleteView.as_view(http_method_names=['delete']), name='agreement-amendment-type-del'),
    # url(r'^agreements/(?P<pk>\d+)/interventions/$', view=AgreementInterventionsListAPIView.as_view(), name='agreement-interventions-list'),

    url(r'^partners/$', view=PartnerOrganizationListAPIView.as_view(http_method_names=['get', 'post']), name='partner-list'),
    url(r'^partners/hact/$', view=PartnerOrganizationHactAPIView.as_view(http_method_names=['get', ]), name='partner-hact'),
    url(r'^partners/(?P<pk>\d+)/$', view=PartnerOrganizationDetailAPIView.as_view(http_method_names=['get', 'patch']), name='partner-detail'),
    url(r'^partners/assessments/(?P<pk>\d+)/$', view=PartnerOrganizationAssessmentDeleteView.as_view(http_method_names=['delete', ]), name='partner-assessment-del'),
    url(r'^partners/add/$', view=PartnerOrganizationAddView.as_view(http_method_names=['post']), name='partner-add'),

    # url(r'^partners/(?P<pk>\d+)/interventions/$', view=PartnerInterventionListAPIView.as_view(), name='partner-interventions-list'),
    # url(r'^partners/(?P<partner_pk>\d+)/agreements/$', view=AgreementListAPIView.as_view(), name='parter-agreement-list'),
    # url(r'^partners/(?P<partner_pk>\d+)/agreements/(?P<pk>\d+)/interventions/$', view=AgreementInterventionsListAPIView.as_view(), name='partner-agreement-interventions-list'),

    url(r'^partners/(?P<partner_pk>\d+)/staff-members/$', view=PartnerStaffMemberListAPIVIew.as_view(http_method_names=['get']), name='parter-staff-members-list'),
    # url(r'^staff-members/$', view=PartnerStaffMemberListAPIVIew.as_view(), name='staff-member-list'),
    # url(r'^staff-members/(?P<pk>\d+)/$', view=PartnerStaffMemberDetailAPIView.as_view(), name='staff-member-detail'),
    # url(r'^staff-members/(?P<pk>\d+)/properties/$', view=PartnerStaffMemberPropertiesAPIView.as_view(), name='staff-member-properties'),
    url(r'^partnership-dash/(?P<ct_pk>\d+)/(?P<office_pk>\d+)/$', view=PartnershipDashboardAPIView.as_view(), name='partnership-dash-with-ct-office'),
    url(r'^partnership-dash/(?P<ct_pk>\d+)/$', view=PartnershipDashboardAPIView.as_view(), name='partnership-dash-with-ct'),
    url(r'^partnership-dash/$', view=PartnershipDashboardAPIView.as_view(), name='partnership-dash'),


    url(r'^interventions/$', view=InterventionListAPIView.as_view(http_method_names=['get', 'post']), name='intervention-list'),
    url(r'^interventions/dash/$', view=InterventionListDashView.as_view(http_method_names=['get', 'post']), name='intervention-list-dash'),
    url(r'^interventions/(?P<pk>\d+)/$', view=InterventionDetailAPIView.as_view(http_method_names=['get', 'patch']), name='intervention-detail'),
    url(r'^interventions/budgets/(?P<pk>\d+)/$', view=InterventionBudgetDeleteView.as_view(http_method_names=['delete', ]), name='intervention-budget-del'),
    url(r'^interventions/planned-visits/(?P<pk>\d+)/$', view=InterventionPlannedVisitsDeleteView.as_view(http_method_names=['delete', ]), name='intervention-visits-del'),
    url(r'^interventions/attachments/(?P<pk>\d+)/$', view=InterventionAttachmentDeleteView.as_view(http_method_names=['delete', ]), name='intervention-attachments-del'),
    url(r'^interventions/results/(?P<pk>\d+)/$', view=InterventionResultLinkDeleteView.as_view(http_method_names=['delete', ]), name='intervention-results-del'),
    url(r'^interventions/amendments/(?P<pk>\d+)/$', view=InterventionAmendmentDeleteView.as_view(http_method_names=['delete', ]), name='intervention-amendments-del'),
    url(r'^interventions/sector-locations/(?P<pk>\d+)/$', view=InterventionSectorLocationLinkDeleteView.as_view(http_method_names=['delete', ]), name='intervention-sector-locations-del'),
    url(r'^interventions/map/$', view=InterventionListMapView.as_view(http_method_names=['get', ]), name='intervention-map'),
    # url(r'^interventions/(?P<pk>\d+)/$', view=InterventionDetailAPIView.as_view(), name='intervention-detail'),

    # TODO: figure this out
    # url(r'^partners/interventions/$', view=InterventionsView.as_view()),
    url(r'^dropdowns/static/$', view=PmpStaticDropdownsListApiView.as_view(http_method_names=['get']), name='dropdown-static-list'),
    url(r'^dropdowns/pmp/$', view=PMPDropdownsListApiView.as_view(http_method_names=['get']), name='dropdown-pmp-list'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
