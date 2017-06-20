from __future__ import absolute_import

from django.conf.urls import include, url

from rest_framework_nested import routers

from audit.views import (
    AuditOrganizationViewSet, AuditViewSet,
    EngagementViewSet, MicroAssessmentViewSet, SpotCheckViewSet,
    PurchaseOrderViewSet, AuditOrganizationStaffMembersViewSet,
    EngagementPDFView)


audit_organizations_api = routers.SimpleRouter()
audit_organizations_api.register(r'audit-organizations', AuditOrganizationViewSet, base_name='audit-organizations')

audit_organization_staffm_api = routers.NestedSimpleRouter(audit_organizations_api, r'audit-organizations', lookup='organization')
audit_organization_staffm_api.register(r'staff-members', AuditOrganizationStaffMembersViewSet, base_name='auditorganizationstaffmembers')

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


urlpatterns = [
    url(r'^', include(audit_organizations_api.urls)),
    url(r'^', include(audit_organization_staffm_api.urls)),
    url(r'^', include(purchase_orders_api.urls)),
    url(r'^', include(engagements_api.urls)),
    url(r'^', include(micro_assessments_api.urls)),
    url(r'^', include(spot_checks_api.urls)),
    url(r'^', include(audits_api.urls)),
    url(r'^engagements/(?P<pk>\d+)/pdf/$', EngagementPDFView.as_view(), name='engagement_pdf')
]
