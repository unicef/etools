
from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.audit.views import (AuditorFirmViewSet, AuditorStaffMembersViewSet, AuditViewSet,
                                             EngagementViewSet, MicroAssessmentViewSet, PurchaseOrderViewSet,
                                             SpecialAuditViewSet, SpotCheckViewSet, EngagementActionPointViewSet,
                                             EngagementAttachmentsViewSet, ReportAttachmentsViewSet)
from etools.applications.utils.common.routers import NestedComplexRouter


root_api = routers.SimpleRouter()
root_api.register(r'audit-firms', AuditorFirmViewSet, base_name='audit-firms')
root_api.register(r'purchase-orders', PurchaseOrderViewSet, base_name='purchase-orders')
root_api.register(r'engagements', EngagementViewSet, base_name='engagements')
root_api.register(r'micro-assessments', MicroAssessmentViewSet, base_name='micro-assessments')
root_api.register(r'spot-checks', SpotCheckViewSet, base_name='spot-checks')
root_api.register(r'audits', AuditViewSet, base_name='audits')
root_api.register(r'special-audits', SpecialAuditViewSet, base_name='special-audits')

auditor_staffmember_api = NestedComplexRouter(root_api, r'audit-firms', lookup='auditor_firm')
auditor_staffmember_api.register(r'staff-members', AuditorStaffMembersViewSet, base_name='auditorstaffmembers')

engagement_action_points_api = NestedComplexRouter(root_api, r'engagements', lookup='engagement')
engagement_action_points_api.register(r'action-points', EngagementActionPointViewSet, base_name='action-points')

attachments_api = NestedComplexRouter(root_api, r'engagements')
attachments_api.register(r'engagement-attachments', EngagementAttachmentsViewSet, base_name='engagement-attachments')
attachments_api.register(r'report-attachments', ReportAttachmentsViewSet, base_name='report-attachments')

app_name = 'audit'
urlpatterns = [
    url(r'^', include(auditor_staffmember_api.urls)),
    url(r'^', include(engagement_action_points_api.urls)),
    url(r'^', include(attachments_api.urls)),
    url(r'^', include(root_api.urls)),
]
