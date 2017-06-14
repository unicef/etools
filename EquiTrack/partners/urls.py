from __future__ import absolute_import

from django.conf.urls import patterns, url

from rest_framework_nested import routers

from .views.v1 import (
    InterventionLocationView,
    PortalLoginFailedView,
    PartnerStaffMemberPropertiesView,
    InterventionsViewSet,
    GovernmentInterventionsViewSet,
    PartnershipBudgetViewSet,
    PCASectorViewSet,
    PCAFileViewSet,
    PCAGrantViewSet,
    AmendmentLogViewSet,
    GwPCALocationViewSet,
    IndicatorReportViewSet,
    PcaPDFView,
    PartnerOrganizationsViewSet,
    PartnerStaffMembersViewSet,
    AgreementViewSet,
)

partners_api = routers.SimpleRouter()
partners_api.register(r'partners', PartnerOrganizationsViewSet, base_name='partnerorganizations')

staffm_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
staffm_api.register(r'staff-members', PartnerStaffMembersViewSet, base_name='partnerstaffmembers')

simple_agreements_api = routers.SimpleRouter()
simple_agreements_api.register(r'agreements', AgreementViewSet, base_name='agreements')

agreement_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
agreement_api.register(r'agreements', AgreementViewSet, base_name='agreements')

# interventions_api = routers.SimpleRouter()
interventions_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
interventions_api.register(r'interventions', InterventionsViewSet, base_name='interventions')

simple_interventions_api = routers.SimpleRouter()
simple_interventions_api.register(r'interventions', InterventionsViewSet, base_name='interventions')

# simple_results_api = routers.NestedSimpleRouter(simple_interventions_api, r'interventions', lookup='intervention')
# simple_results_api.register(r'results', InterventionResultsViewSet, base_name='simpleintervention-results')

pcasectors_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcasectors_api.register(r'sectors', PCASectorViewSet, base_name='intervention-sectors')

pcabudgets_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcabudgets_api.register(r'budgets', PartnershipBudgetViewSet, base_name='intervention-budgets')

pcafiles_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcafiles_api.register(r'files', PCAFileViewSet, base_name='intervention-files')

pcagrants_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcagrants_api.register(r'grants', PCAGrantViewSet, base_name='intervention-grants')

pcalocations_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcalocations_api.register(r'locations', GwPCALocationViewSet, base_name='intervention-locations')

pcaamendments_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcaamendments_api.register(r'amendments', AmendmentLogViewSet, base_name='intervention-amendments')

# results_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
# results_api.register(r'results', ResultChainViewSet, base_name='intervention-results')

# intervention_reports_api = routers.NestedSimpleRouter(simple_results_api, r'results', lookup='result')
# intervention_reports_api.register(r'reports', IndicatorReportViewSet, base_name='intervention-reports')

bulk_reports_api = routers.SimpleRouter()
bulk_reports_api.register(r'bulk_reports', IndicatorReportViewSet, base_name='bulk-reports')


urlpatterns = patterns(
    '',
    # remove partner portal for now:
    # url(r'^$', PortalDashView.as_view()),

    url(r'^my_interventions/', InterventionsViewSet.as_view({'get': 'retrieve'}), name='interventions'),
    # url(r'^interventions/(?P<intervention_pk>\d+)/reports/', IndicatorReportViewSet.as_view(), name='interventions'),
    #
    # url(r'^interventions/(?P<intervention_pk>\d+)/reports/', IndicatorReportViewSet.as_view(), name='intervention-reports'),
    #
    # url(r'^interventions/(?P<intervention_pk>\d+)/indicator/(?P<indicator_pk>\d+)/reports/', IndicatorReportViewSet.as_view(), name='intervention-indicator-reports'),
    # url(r'^indicators/bulk_reports/', IndicatorReportViewSet.as_view(), name='indicator-bulk-reports'),

    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^locations/$', InterventionLocationView.as_view(), name='locations'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PcaPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
