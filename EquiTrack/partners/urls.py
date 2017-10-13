from __future__ import absolute_import

from django.conf.urls import url

from .views.v1 import (
    PortalLoginFailedView,
    PartnerStaffMemberPropertiesView,
    PCAPDFView,
)

# simple_results_api = routers.NestedSimpleRouter(simple_interventions_api, r'interventions', lookup='intervention')
# simple_results_api.register(r'results', InterventionResultsViewSet, base_name='simpleintervention-results')

# results_api = routers.NestedSimpleRouter(interventions_api, r'interventions', lookup='intervention')
# results_api.register(r'results', ResultChainViewSet, base_name='intervention-results')

urlpatterns = (
    # remove partner portal for now:
    # url(r'^$', PortalDashView.as_view()),

    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PCAPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
