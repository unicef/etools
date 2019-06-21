from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.tpm.views import (
    ActivityAttachmentLinksView,
    ActivityAttachmentsViewSet,
    ActivityReportAttachmentsViewSet,
    PartnerAttachmentsViewSet,
    TPMActionPointViewSet,
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
tpm_staffmember_api.register(r'staff-members', TPMStaffMembersViewSet, base_name='tpmstaffmembers')

partner_attachments_api = NestedComplexRouter(tpm_partners_api, r'partners')
partner_attachments_api.register(r'attachments', PartnerAttachmentsViewSet, base_name='partner-attachments')

tpm_visits_api = routers.SimpleRouter()
tpm_visits_api.register(r'visits', TPMVisitViewSet, basename='visits')

visit_attachments_api = NestedComplexRouter(tpm_visits_api, r'visits')
visit_attachments_api.register('report-attachments', VisitReportAttachmentsViewSet,
                               base_name='visit-report-attachments')
visit_attachments_api.register('attachments', VisitAttachmentsViewSet,
                               base_name='visit-attachments')
visit_attachments_api.register('activities/attachments', ActivityAttachmentsViewSet,
                               base_name='activity-attachments')
visit_attachments_api.register('activities/report-attachments', ActivityReportAttachmentsViewSet,
                               base_name='activity-report-attachments')
tpm_action_points_api = NestedComplexRouter(tpm_visits_api, r'visits', lookup='tpm_activity__tpm_visit')
tpm_action_points_api.register(r'action-points', TPMActionPointViewSet, base_name='action-points')


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
