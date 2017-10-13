from __future__ import absolute_import

from django.conf.urls import url

from rest_framework_nested import routers

from .views.v1 import (
    PortalLoginFailedView,
    PartnerStaffMemberPropertiesView,
    IndicatorReportViewSet,
    PCAPDFView,
    PartnerOrganizationsViewSet,
    PartnerStaffMembersViewSet,
)

partners_api = routers.SimpleRouter()
partners_api.register(r'partners', PartnerOrganizationsViewSet, base_name='partnerorganizations')

staffm_api = routers.NestedSimpleRouter(partners_api, r'partners', lookup='partner')
staffm_api.register(r'staff-members', PartnerStaffMembersViewSet, base_name='partnerstaffmembers')

# simple_results_api = routers.NestedSimpleRouter(simple_interventions_api, r'interventions', lookup='intervention')
# simple_results_api.register(r'results', InterventionResultsViewSet, base_name='simpleintervention-results')

# results_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
# results_api.register(r'results', ResultChainViewSet, base_name='intervention-results')

# intervention_reports_api = routers.NestedSimpleRouter(simple_results_api, r'results', lookup='result')
# intervention_reports_api.register(r'reports', IndicatorReportViewSet, base_name='intervention-reports')

bulk_reports_api = routers.SimpleRouter()
bulk_reports_api.register(r'bulk_reports', IndicatorReportViewSet, base_name='bulk-reports')


urlpatterns = (
    # remove partner portal for now:
    # url(r'^$', PortalDashView.as_view()),

    # url(r'^interventions/(?P<intervention_pk>\d+)/reports/', IndicatorReportViewSet.as_view(), name='interventions'),
    #
    # url(r'^interventions/(?P<intervention_pk>\d+)/reports/', IndicatorReportViewSet.as_view(),
    #     name='intervention-reports'),
    #
    # url(r'^interventions/(?P<intervention_pk>\d+)/indicator/(?P<indicator_pk>\d+)/reports/',
    #     IndicatorReportViewSet.as_view(), name='intervention-indicator-reports'),
    # url(r'^indicators/bulk_reports/', IndicatorReportViewSet.as_view(), name='indicator-bulk-reports'),

    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PCAPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
