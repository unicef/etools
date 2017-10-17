from __future__ import absolute_import

from django.conf.urls import include, url

from rest_framework_nested import routers

from audit.views import (
    AuditorFirmViewSet, AuditViewSet, SpecialAuditViewSet,
    EngagementViewSet, MicroAssessmentViewSet, SpotCheckViewSet,
    PurchaseOrderViewSet, AuditorStaffMembersViewSet,
    AuditPDFView, SpotCheckPDFView, MicroAssessmentPDFView)
from utils.common.routers import NestedComplexRouter

auditor_firms_api = routers.SimpleRouter()
auditor_firms_api.register(r'audit-firms', AuditorFirmViewSet, base_name='audit-firms')

auditor_staffmember_api = NestedComplexRouter(auditor_firms_api, r'audit-firms', lookup='auditor_firm')
auditor_staffmember_api.register(r'staff-members', AuditorStaffMembersViewSet, base_name='auditorstaffmembers')

purchase_orders_api = routers.SimpleRouter()
purchase_orders_api.register(r'purchase-orders', PurchaseOrderViewSet, base_name='purchase-orders')

engagements_api = routers.SimpleRouter()
engagements_api.register(r'engagements', EngagementViewSet, base_name='engagements')

micro_assessments_api = routers.SimpleRouter()
micro_assessments_api.register(r'micro-assessments', MicroAssessmentViewSet, base_name='micro-assessments')

spot_checks_api = routers.SimpleRouter()
spot_checks_api.register(r'spot-checks', SpotCheckViewSet, base_name='spot-checks')

audits_api = routers.SimpleRouter()
audits_api.register('audits', AuditViewSet, base_name='audits')

special_audits_api = routers.SimpleRouter()
special_audits_api.register(r'special-audits', SpecialAuditViewSet, base_name='special-audits')


urlpatterns = [
    url(r'^', include(auditor_firms_api.urls)),
    url(r'^', include(auditor_staffmember_api.urls)),
    url(r'^', include(purchase_orders_api.urls)),
    url(r'^', include(engagements_api.urls)),
    url(r'^audits/(?P<pk>\d+)/pdf/$', AuditPDFView.as_view(), name='audit_pdf'),
    url(r'^spot-checks/(?P<pk>\d+)/pdf/$', SpotCheckPDFView.as_view(), name='spot-check_pdf'),
    url(r'^micro-assessments/(?P<pk>\d+)/pdf/$', MicroAssessmentPDFView.as_view(), name='micro-assessment_pdf'),
    url(r'^', include(micro_assessments_api.urls)),
    url(r'^', include(spot_checks_api.urls)),
    url(r'^', include(audits_api.urls)),
    url(r'^', include(special_audits_api.urls)),
]
