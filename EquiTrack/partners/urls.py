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
    PartnershipBudgetViewSet,
    PCASectorViewSet,
    PCAFileViewSet,
    PCAGrantViewSet,
    AmendmentLogViewSet,
    GwPCALocationViewSet,
    ResultChainViewSet,
    IndicatorReportViewSet,
    PcaPDFView,
)

interventions_api = routers.SimpleRouter()
interventions_api.register(r'interventions', InterventionsViewSet, base_name='interventions')

pcasectors_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcasectors_api.register(r'pcasector', PCASectorViewSet, base_name='intervention-pcasector')

pcabudgets_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcabudgets_api.register(r'pcabudgets', PartnershipBudgetViewSet, base_name='intervention-pcabudgets')

pcafiles_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcafiles_api.register(r'pcafiles', PCAFileViewSet, base_name='intervention-pcafiles')

pcagrants_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcagrants_api.register(r'pcagrants', PCAGrantViewSet, base_name='intervention-pcagrants')

pcalocations_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcalocations_api.register(r'pcalocations', GwPCALocationViewSet, base_name='intervention-pcalocations')

pcaamendments_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
pcaamendments_api.register(r'pcaamendments', AmendmentLogViewSet, base_name='intervention-pcaamendments')

results_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
results_api.register(r'results', ResultChainViewSet, base_name='intervention-results')

reports_api = routers.NestedSimpleRouter(results_api, r'results', lookup='result')
reports_api.register(r'reports', IndicatorReportViewSet, base_name='intervention-reports')


urlpatterns = patterns(
    '',
    url(r'^$', PortalDashView.as_view()),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^locations/$', InterventionLocationView.as_view(), name='locations'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PcaPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
