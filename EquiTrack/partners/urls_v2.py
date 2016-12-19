from django.conf.urls import url

from partners.views.v2 import (
    GovernmentInterventionExportAPIView,
    GovernmentInterventionListAPIView,
    GovernmentInterventionDetailAPIView,
)

urlpatterns = (
    url(r'^partners/interventions/$', view=GovernmentInterventionListAPIView.as_view(), name='interventions-list'),
    url(r'^partners/interventions/(?P<pk>\d+)/$', view=GovernmentInterventionDetailAPIView.as_view(), name='interventions-detail'),
    url(r'^partners/interventions/export/$', view=GovernmentInterventionExportAPIView.as_view(), name='interventions-list-export'),
)
