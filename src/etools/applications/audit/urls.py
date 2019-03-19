from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.audit import views

root_api = routers.SimpleRouter()
root_api.register(r'audit-firms', views.AuditorFirmViewSet, base_name='audit-firms')
root_api.register(r'purchase-orders', views.PurchaseOrderViewSet, base_name='purchase-orders')
root_api.register(r'engagements', views.EngagementViewSet, base_name='engagements')
root_api.register(r'micro-assessments', views.MicroAssessmentViewSet, base_name='micro-assessments')
root_api.register(r'spot-checks', views.SpotCheckViewSet, base_name='spot-checks')
root_api.register(r'staff-spot-checks', views.StaffSpotCheckViewSet, base_name='staff-spot-checks')
root_api.register(r'audits', views.AuditViewSet, base_name='audits')
root_api.register(r'special-audits', views.SpecialAuditViewSet, base_name='special-audits')

auditor_staffmember_api = NestedComplexRouter(root_api, r'audit-firms', lookup='auditor_firm')
auditor_staffmember_api.register(r'staff-members', views.AuditorStaffMembersViewSet, base_name='auditorstaffmembers')

engagement_action_points_api = NestedComplexRouter(root_api, r'engagements', lookup='engagement')
engagement_action_points_api.register(r'action-points', views.EngagementActionPointViewSet, base_name='action-points')

attachments_api = NestedComplexRouter(root_api, r'engagements')
attachments_api.register(r'engagement-attachments', views.EngagementAttachmentsViewSet, base_name='engagement-attachments')
attachments_api.register(r'report-attachments', views.ReportAttachmentsViewSet, base_name='report-attachments')

app_name = 'audit'
urlpatterns = [
    url(r'^', include(auditor_staffmember_api.urls)),
    url(r'^', include(engagement_action_points_api.urls)),
    url(r'^', include(attachments_api.urls)),
    url(r'^', include(root_api.urls)),
    url(
        r'^engagement/(?P<object_pk>\d+)/links',
        view=views.EngagementAttachmentLinksView.as_view(),
        name='engagement-links'
    ),
    url(
        r'^spot-check/(?P<object_pk>\d+)/links',
        view=views.SpotCheckAttachmentLinksView.as_view(),
        name='spot-check-links'
    ),
    url(
        r'^micro-assessment/(?P<object_pk>\d+)/links',
        view=views.MicroAssessmentAttachmentLinksView.as_view(),
        name='micro-assessment-links'
    ),
    url(
        r'^audit/(?P<object_pk>\d+)/links',
        view=views.AuditAttachmentLinksView.as_view(),
        name='audit-links'
    ),
    url(
        r'^special-audit/(?P<object_pk>\d+)/links',
        view=views.SpecialAuditAttachmentLinksView.as_view(),
        name='special-audit-links'
    ),
]
