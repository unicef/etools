from __future__ import absolute_import

from django.conf.urls import patterns, url

from .views.v1 import (
    PortalLoginFailedView,
    PartnerStaffMemberPropertiesView,
    InterventionsViewSet,
    PcaPDFView,
)

urlpatterns = patterns(
    '',

    url(r'^my_interventions/', InterventionsViewSet.as_view({'get': 'retrieve'}), name='interventions'),
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PcaPDFView.as_view(), name='pca_pdf'),

    url(r'^staffmember/(?P<pk>\d+)/$', PartnerStaffMemberPropertiesView.as_view()),
)
