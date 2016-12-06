from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from .views.v2 import (
    InterventionListAPIView,
    InterventionDetailAPIView,
    PartnerInterventionListAPIView
)

urlpatterns = (
    url(r'^interventions/$', view=InterventionListAPIView.as_view(), name='intervention-list'),
    url(r'^interventions/(?P<pk>\d+)/$', view=InterventionDetailAPIView.as_view(), name='intervention-detail'),
    # url(r'^partners/(?P<pk>\d+)/$', view=PartnerOrganizationDetailAPIView.as_view(), name='partner-detail'),
    # url(r'^partners/(?P<pk>\d+)/interventions/$', view=PartnerInterventionListAPIView.as_view(), name='partner-interventions-list'),
)

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
