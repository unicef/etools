
from django.conf.urls import url, patterns, include

from et2f.views import TravelListViewSet, TravelDetailsViewSet, StaticDataView, PermissionMatrixView, CurrentUserView


travel_list = TravelListViewSet.as_view({'get': 'list',
                                         'post': 'create'})
travel_list_export = TravelListViewSet.as_view({'get': 'export'})
travel_list_state_change = TravelListViewSet.as_view({'post': 'state_change'})

travel_details = TravelDetailsViewSet.as_view({'get': 'retrieve',
                                               'put': 'update',
                                               'patch': 'partial_update'})
travel_details_state_change = TravelDetailsViewSet.as_view({'post': 'partial_update',
                                                            'put': 'partial_update',
                                                            'patch': 'partial_update'})

details_state_changes_pattern = r'^(?P<pk>[0-9]+)/(?P<transition_name>submit_for_approval|approve|reject|cancel|plan|' \
                                r'send_for_payment|submit_certificate|approve_cetificate|reject_certificate|' \
                                r'mark_as_certified|mark_as_completed)/$'

travel_pattens = patterns(
    '',
    url(r'^$', travel_list, name='list'),
    url(r'^export/$', travel_list_export, name='list_export'),
    url(r'^(?P<transition_name>save_and_submit)/$', travel_list_state_change, name='list_state_change'),

    url(r'^(?P<pk>[0-9]+)/$', travel_details, name='details'),
    url(details_state_changes_pattern, travel_details_state_change, name='details_state_change'),
)

urlpatterns = patterns(
    '',
    url(r'^travels/', include(travel_pattens, namespace='travels')),
    url(r'^static_data/$', StaticDataView.as_view(), name='static_data'),
    url(r'^permission_matrix/$', PermissionMatrixView.as_view(), name='permission_matrix'),
    url(r'^me/$', CurrentUserView.as_view(), name='current_user'),
)