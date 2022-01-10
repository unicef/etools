from django.urls import include, re_path

from etools.applications.t2f.models import Travel
from etools.applications.t2f.views.dashboard import TravelDashboardViewSet
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

details_state_changes_pattern = r"^(?P<transition_name>{})/$".format("|".join(Travel.TRANSACTIONS))

travel_details_patterns = ((
    re_path(r'^$', travel_details, name='index'),
    re_path(r'^attachments/$', travel_attachments, name='attachments'),
    re_path(r'^attachments/(?P<attachment_pk>[0-9]+)/$', travel_attachment_details, name='attachment_details'),
    re_path(details_state_changes_pattern, travel_details_state_change, name='state_change'),
    re_path(r'duplicate_travel/$', clone_travel_for_secondary_traveler, name='clone_for_secondary_traveler'),
), 'details')


travel_list_patterns = ((
    re_path(r'^$', travel_list, name='index'),
    re_path(r'^(?P<transition_name>save_and_submit|mark_as_completed)/$', travel_list_state_change, name='state_change'),
    re_path(r'^export/$', TravelActivityExport.as_view(), name='activity_export'),
    re_path(r'^travel-admin-export/$', TravelAdminExport.as_view(), name='travel_admin_export'),
    re_path(r'^activities/partnership/(?P<partnership_pk>[0-9]+)/',
            TravelActivityPerInterventionViewSet.as_view({'get': 'list'}), name='activities-intervention'),
    re_path(r'^activities/(?P<partner_organization_pk>[0-9]+)/', TravelActivityViewSet.as_view({'get': 'list'}),
            name='activities'),
    re_path(r'^dashboard', travel_dashboard_list, name='dashboard'),
), 'list')


travel_patterns = ((
    re_path(r'^', include(travel_list_patterns)),
    re_path(r'^(?P<travel_pk>[0-9]+)/', include(travel_details_patterns)),
), 'travels')


urlpatterns = ((
    re_path(r'^travels/', include(travel_patterns)),
    re_path(r'^static_data/$', StaticDataView.as_view(), name='static_data'),
    re_path(r'^permission_matrix/$', PermissionMatrixView.as_view(), name='permission_matrix'),
), 't2f')
