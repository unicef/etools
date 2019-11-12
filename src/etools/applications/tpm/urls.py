from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.tpm.views import (
    ActivityAttachmentLinksView,
    ActivityAttachmentsViewSet,
    ActivityReportAttachmentsViewSet,
    PartnerAttachmentsViewSet,
    TPMActionPointViewSet,
    TPMActivityViewSet,
    TPMPartnerViewSet,
    TPMStaffMembersViewSet,
    TPMVisitViewSet,
    VisitAttachmentLinksView,
    VisitAttachmentsViewSet,
    VisitReportAttachmentsViewSet,
)

tpm_partners_api = routers.SimpleRouter()
tpm_partners_api.register(r'partners', TPMPartnerViewSet, basename='partners')

tpm_staffmember_api = NestedComplexRouter(tpm_partners_api, r'partners', lookup='tpm_partner')
tpm_staffmember_api.register(r'staff-members', TPMStaffMembersViewSet, basename='tpmstaffmembers')

partner_attachments_api = NestedComplexRouter(tpm_partners_api, r'partners')
partner_attachments_api.register(r'attachments', PartnerAttachmentsViewSet, basename='partner-attachments')

tpm_visits_api = routers.SimpleRouter()
tpm_visits_api.register(r'visits', TPMVisitViewSet, basename='visits')
tpm_visits_api.register(r'activities', TPMActivityViewSet, basename='activities')

visit_attachments_api = NestedComplexRouter(tpm_visits_api, r'visits')
visit_attachments_api.register('report-attachments', VisitReportAttachmentsViewSet,
                               basename='visit-report-attachments')
visit_attachments_api.register('attachments', VisitAttachmentsViewSet,
                               basename='visit-attachments')
visit_attachments_api.register('activities/attachments', ActivityAttachmentsViewSet,
                               basename='activity-attachments')
visit_attachments_api.register('activities/report-attachments', ActivityReportAttachmentsViewSet,
                               basename='activity-report-attachments')
tpm_action_points_api = NestedComplexRouter(tpm_visits_api, r'visits', lookup='tpm_activity__tpm_visit')
tpm_action_points_api.register(r'action-points', TPMActionPointViewSet, basename='action-points')


app_name = 'tpm'
urlpatterns = [
    url(r'^', include(tpm_staffmember_api.urls)),
    url(r'^', include(partner_attachments_api.urls)),
    url(r'^', include(tpm_partners_api.urls)),
    url(r'^', include(tpm_action_points_api.urls)),
    url(r'^', include(visit_attachments_api.urls)),
    url(r'^', include(tpm_visits_api.urls)),
    url(
        r'^visits/activities/(?P<object_pk>\d+)/links',
        view=ActivityAttachmentLinksView.as_view(),
        name='activity-links'
    ),
    url(
        r'^visits/(?P<object_pk>\d+)/links',
        view=VisitAttachmentLinksView.as_view(),
        name='visit-links'
    ),
]
