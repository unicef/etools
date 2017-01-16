from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from .views.v1 import InterventionsView
from .views.partner_organization_v2 import (
    PartnerOrganizationListAPIView, PartnerOrganizationDetailAPIView,
)
from .views.agreements_v2 import (
    AgreementListAPIView,
    AgreementDetailAPIView
)
from views.interventions_v2 import (
    InterventionListAPIView,
    InterventionDetailAPIView
)
from views.v2 import PmpStaticDropdownsListApiView


# http://www.django-rest-framework.org/api-guide/format-suffixes/

urlpatterns = (

    url(r'^agreements/$', view=AgreementListAPIView.as_view(), name='agreement-list'),

    url(r'^agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(), name='agreement-detail'),
    # url(r'^agreements/(?P<pk>\d+)/interventions/$', view=AgreementInterventionsListAPIView.as_view(), name='agreement-interventions-list'),

    url(r'^partners/$', view=PartnerOrganizationListAPIView.as_view(http_method_names=['get', 'post']), name='partner-list'),
    url(r'^partners/(?P<pk>\d+)/$', view=PartnerOrganizationDetailAPIView.as_view(http_method_names=['get', 'patch']), name='partner-detail'),


    # url(r'^partners/(?P<pk>\d+)/interventions/$', view=PartnerInterventionListAPIView.as_view(), name='partner-interventions-list'),
    # url(r'^partners/(?P<partner_pk>\d+)/agreements/$', view=AgreementListAPIView.as_view(), name='parter-agreement-list'),
    # url(r'^partners/(?P<partner_pk>\d+)/agreements/(?P<pk>\d+)/interventions/$', view=AgreementInterventionsListAPIView.as_view(), name='partner-agreement-interventions-list'),
    # url(r'^partners/(?P<partner_pk>\d+)/staff-members/$', view=PartnerStaffMemberListAPIVIew.as_view(), name='parter-staff-members-list'),
    # url(r'^staff-members/$', view=PartnerStaffMemberListAPIVIew.as_view(), name='staff-member-list'),
    # url(r'^staff-members/(?P<pk>\d+)/$', view=PartnerStaffMemberDetailAPIView.as_view(), name='staff-member-detail'),
    # url(r'^staff-members/(?P<pk>\d+)/properties/$', view=PartnerStaffMemberPropertiesAPIView.as_view(), name='staff-member-properties'),


    url(r'^interventions/$', view=InterventionListAPIView.as_view(http_method_names=['get', 'post']), name='intervention-list'),
    url(r'^interventions/(?P<pk>\d+)/$', view=InterventionDetailAPIView.as_view(http_method_names=['get', 'patch']), name='intervention-detail'),
    # url(r'^interventions/(?P<pk>\d+)/$', view=InterventionDetailAPIView.as_view(), name='intervention-detail'),
    # TODO: figure this out
    # url(r'^partners/interventions/$', view=InterventionsView.as_view()),
    url(r'^dropdowns/$', view=PmpStaticDropdownsListApiView.as_view(http_method_names=['get']), name='dropdown-list'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
