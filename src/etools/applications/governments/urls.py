from django.urls import path

from etools.applications.governments.views.gdd import (
    GDDListCreateView,
    GDDRetrieveResultsStructure,
    GDDRetrieveUpdateView,
)
from etools.applications.governments.views.government import (
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
]
