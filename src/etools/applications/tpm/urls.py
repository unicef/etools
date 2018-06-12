
from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.tpm.views import (
    TPMActionPointViewSet, TPMPartnerViewSet, TPMStaffMembersViewSet, TPMVisitViewSet,)
from etools.applications.utils.common.routers import NestedComplexRouter

tpm_partners_api = routers.SimpleRouter()
tpm_partners_api.register(r'partners', TPMPartnerViewSet, base_name='partners')

tpm_staffmember_api = NestedComplexRouter(tpm_partners_api, r'partners', lookup='tpm_partner')
tpm_staffmember_api.register(r'staff-members', TPMStaffMembersViewSet, base_name='tpmstaffmembers')

tpm_visits_api = routers.SimpleRouter()
tpm_visits_api.register(r'visits', TPMVisitViewSet, base_name='visits')

tpm_action_points_api = NestedComplexRouter(tpm_visits_api, r'visits', lookup='tpm_activity__tpm_visit')
tpm_action_points_api.register(r'action-points', TPMActionPointViewSet, base_name='action-points')


app_name = 'tpm'
urlpatterns = [
    url(r'^', include(tpm_staffmember_api.urls)),
    url(r'^', include(tpm_partners_api.urls)),
    url(r'^', include(tpm_action_points_api.urls)),
    url(r'^', include(tpm_visits_api.urls)),
]
