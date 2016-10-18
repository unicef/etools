from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.conf.urls import patterns, url, include

from rest_framework_nested import routers

from .views import (
    InterventionLocationView,
    PortalDashView,
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
    ResultChainViewSet,
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

agreement_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
agreement_api.register(r'agreements', AgreementViewSet, base_name='agreements')

# interventions_api = routers.SimpleRouter()
interventions_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
interventions_api.register(r'interventions', InterventionsViewSet, base_name='interventions')

government_interventions_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
government_interventions_api.register(r'government_interventions', GovernmentInterventionsViewSet, base_name='government_interventions')

simple_government_interventions_api = routers.SimpleRouter()
simple_government_interventions_api.register(r'government_interventions', GovernmentInterventionsViewSet, base_name='government_interventions')

simple_interventions_api = routers.SimpleRouter()
simple_interventions_api.register(r'interventions', InterventionsViewSet, base_name='interventions')

simple_results_api = routers.NestedSimpleRouter(simple_interventions_api, r'interventions', lookup='intervention')
simple_results_api.register(r'results', ResultChainViewSet, base_name='simpleintervention-results')

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

results_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
results_api.register(r'results', ResultChainViewSet, base_name='intervention-results')

intervention_reports_api = routers.NestedSimpleRouter(simple_results_api, r'results', lookup='result')
intervention_reports_api.register(r'reports', IndicatorReportViewSet, base_name='intervention-reports')

bulk_reports_api = routers.SimpleRouter()
bulk_reports_api.register(r'bulk_reports', IndicatorReportViewSet, base_name='bulk-reports')


urlpatterns = patterns(
    '',
    url(r'^$', PortalDashView.as_view()),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^locations/$', InterventionLocationView.as_view(), name='locations'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PcaPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
