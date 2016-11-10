from django.conf.urls import patterns, url

from .views_v2 import (
    AgreementListAPIView,
    AgreementDetailAPIView,
    AgreementInterventionsListAPIView,
)

urlpatterns = (
    url(r'^agreements/$', view=AgreementListAPIView.as_view(), name='agreement-list'),
    url(r'^agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(), name='agreement-detail'),
    url(r'^partners/(?P<partner_pk>\d+)/agreements/$', view=AgreementListAPIView.as_view(), name='parter-agreement-list'),
    url(r'^partners/(?P<partner_pk>\d+)/agreements/(?P<pk>\d+)/$', view=AgreementDetailAPIView.as_view(), name='partner-agreement-detail'),
    url(r'^partners/(?P<partner_pk>\d+)/agreements/(?P<pk>\d+)/interventions/$', view=AgreementInterventionsListAPIView.as_view(), name='partner-agreement-interventions-list'),
)
