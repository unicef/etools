from django.urls import path

from etools.applications.governments.views.gov_intervention import GovInterventionListCreateView, \
    GovInterventionRetrieveUpdateView
from etools.applications.governments.views.government import GovernmentOrganizationListAPIView, GovernmentStaffMemberListAPIVIew

app_name = 'governments'


urlpatterns = [
    path(
        'governments/',
        view=GovernmentOrganizationListAPIView.as_view(
            http_method_names=['get'],
        ),
        name='government-list',
    ),
    path(
        'governments/<int:partner_pk>/staff-members/',
        view=GovernmentStaffMemberListAPIVIew.as_view(
            http_method_names=['get'],
        ),
        name='government-staff-members-list',
    ),
    path(
        'interventions/',
        view=GovInterventionListCreateView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='gov-intervention-list',
    ),
    path(
        'interventions/<int:pk>/',
        view=GovInterventionRetrieveUpdateView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='gov-intervention-detail',
    ),
]
