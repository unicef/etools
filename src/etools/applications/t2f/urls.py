from django.conf.urls import include, url

from etools.applications.t2f.models import Travel
from etools.applications.t2f.views.dashboard import ActionPointDashboardViewSet, TravelDashboardViewSet
from etools.applications.t2f.views.exports import TravelActivityExport, TravelAdminExport
from etools.applications.t2f.views.generics import PermissionMatrixView, StaticDataView
from etools.applications.t2f.views.travel import (
    TravelActivityPerInterventionViewSet,
    TravelActivityViewSet,
    TravelAttachmentViewSet,
    TravelDetailsViewSet,
    TravelListViewSet,
)

app_name = 't2f'
travel_list = TravelListViewSet.as_view({'get': 'list',
                                         'post': 'create'})
travel_dashboard_list = TravelDashboardViewSet.as_view({'get': 'list'})

travel_list_state_change = TravelListViewSet.as_view({'post': 'create'})

travel_details = TravelDetailsViewSet.as_view({'get': 'retrieve',
                                               'put': 'update',
                                               'patch': 'partial_update'})
travel_details_state_change = TravelDetailsViewSet.as_view({'post': 'partial_update',
                                                            'put': 'partial_update',
                                                            'patch': 'partial_update'})
travel_attachments = TravelAttachmentViewSet.as_view({'get': 'list',
                                                      'post': 'create'})
travel_attachment_details = TravelAttachmentViewSet.as_view({'delete': 'destroy'})

clone_travel_for_secondary_traveler = TravelDetailsViewSet.as_view({'post': 'clone_for_secondary_traveler'})

action_points_dashboard_list = ActionPointDashboardViewSet.as_view({'get': 'list'})

details_state_changes_pattern = r"^(?P<transition_name>{})/$".format("|".join(Travel.TRANSACTIONS))

travel_details_patterns = ((
    url(r'^$', travel_details, name='index'),
    url(r'^attachments/$', travel_attachments, name='attachments'),
    url(r'^attachments/(?P<attachment_pk>[0-9]+)/$', travel_attachment_details, name='attachment_details'),
    url(details_state_changes_pattern, travel_details_state_change, name='state_change'),
    url(r'duplicate_travel/$', clone_travel_for_secondary_traveler, name='clone_for_secondary_traveler'),
), 'details')


travel_list_patterns = ((
    url(r'^$', travel_list, name='index'),
    url(r'^(?P<transition_name>save_and_submit|mark_as_completed)/$', travel_list_state_change, name='state_change'),
    url(r'^export/$', TravelActivityExport.as_view(), name='activity_export'),
    url(r'^travel-admin-export/$', TravelAdminExport.as_view(), name='travel_admin_export'),
    url(r'^activities/partnership/(?P<partnership_pk>[0-9]+)/',
        TravelActivityPerInterventionViewSet.as_view({'get': 'list'}), name='activities-intervention'),
    url(r'^activities/(?P<partner_organization_pk>[0-9]+)/', TravelActivityViewSet.as_view({'get': 'list'}),
        name='activities'),
    url(r'^dashboard', travel_dashboard_list, name='dashboard'),
), 'list')


travel_patterns = ((
    url(r'^', include(travel_list_patterns)),
    url(r'^(?P<travel_pk>[0-9]+)/', include(travel_details_patterns)),
), 'travels')


action_points_patterns = ((
    url(r'^dashboard/$', action_points_dashboard_list, name='dashboard'),
), 'action_points')

urlpatterns = ((
    url(r'^travels/', include(travel_patterns)),
    url(r'^static_data/$', StaticDataView.as_view(), name='static_data'),
    url(r'^permission_matrix/$', PermissionMatrixView.as_view(), name='permission_matrix'),
    url(r'^action_points/', include(action_points_patterns)),
), 't2f')
