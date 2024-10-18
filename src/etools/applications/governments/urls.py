from django.urls import path

from etools.applications.governments.views.gdd import (
    GDDListCreateView,
    GDDRetrieveResultsStructure,
    GDDRetrieveUpdateView, GDDResultLinkListCreateView,
)
from etools.applications.governments.views.government import (
    EWPActivityListView,
    EWPKeyInterventionListView,
    EWPOutputListView,
    GovernmentEWPListView,
    GovernmentOrganizationListAPIView,
    GovernmentStaffMemberListAPIVIew,
)

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
        'gdds/',
        view=GDDListCreateView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='gdd-list',
    ),
    path(
        'gdds/<int:pk>/',
        view=GDDRetrieveUpdateView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='gdd-detail',
    ),
    path(
        'gdds/<int:pk>/results-structure/',
        view=GDDRetrieveResultsStructure.as_view(
            http_method_names=['get'],
        ),
        name='gdd-detail-results-structure',
    ),
    path(
      'dropdown-options/e-workplans/',
      view=GovernmentEWPListView.as_view(
          http_method_names=['get'],
      ),
      name='e-workplan-list',
    ),
    path(
        'dropdown-options/ewp-outputs/',
        view=EWPOutputListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-output-list',
    ),
    path(
        'dropdown-options/ewp-key-interventions/',
        view=EWPKeyInterventionListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-key-intervention-list',
    ),
    path(
        'dropdown-options/ewp-activities/',
        view=EWPActivityListView.as_view(
            http_method_names=['get'],
        ),
        name='ewp-activity-list',
    ),
    path(
        'gdds/<int:pk>/result-links/',
        view=GDDResultLinkListCreateView.as_view(
            http_method_names=['get', 'post']
        ),
        name='gdd-result-links-list'),
]
