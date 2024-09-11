from django.urls import path

from etools.applications.governments.views.digital_document import DigitalDocumentListCreateView, \
    DigitalDocumentRetrieveUpdateView
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
        'digital-documents/',
        view=DigitalDocumentListCreateView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='digital-document-list',
    ),
    path(
        'digital-documents/<int:pk>/',
        view=DigitalDocumentRetrieveUpdateView.as_view(
            http_method_names=['get', 'patch'],
        ),
        name='digital-document-detail',
    ),
]
