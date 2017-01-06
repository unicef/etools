
from django.conf.urls import url, patterns, include

from t2f.views import TravelListViewSet, TravelDetailsViewSet, StaticDataView, PermissionMatrixView, \
    TravelAttachmentViewSet


travel_list = TravelListViewSet.as_view({'get': 'list',
                                         'post': 'create'})
travel_list_export = TravelListViewSet.as_view({'get': 'export'})
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
clone_travel_for_driver = TravelDetailsViewSet.as_view({'post': 'clone_for_driver'})

details_state_changes_pattern = r'^(?P<transition_name>submit_for_approval|approve|reject|cancel|plan|' \
                                r'send_for_payment|submit_certificate|approve_certificate|reject_certificate|' \
                                r'mark_as_certified|mark_as_completed)/$'

travel_details_patterns = patterns(
    '',
    url(r'^$', travel_details, name='index'),
    url(r'^attachments/$', travel_attachments, name='attachments'),
    url(r'^attachments/(?P<attachment_pk>[0-9]+)/$', travel_attachment_details,
        name='attachment_details'),
    url(details_state_changes_pattern, travel_details_state_change, name='state_change'),
    url(r'duplicate_travel/$', clone_travel_for_secondary_traveler,
        name='clone_for_secondary_traveler'),
    url(r'^add_driver/$', clone_travel_for_driver, name='clone_for_driver'),
)

travel_list_patterns = patterns(
    '',
    url(r'^$', travel_list, name='index'),
    url(r'^export/$', travel_list_export, name='export'),
    url(r'^(?P<transition_name>save_and_submit)/$', travel_list_state_change, name='state_change'),
)


travel_pattens = patterns(
    '',
    url(r'^', include(travel_list_patterns, namespace='list')),
    url(r'^(?P<travel_pk>[0-9]+)/', include(travel_details_patterns, namespace='details')),
)

urlpatterns = patterns(
    '',
    url(r'^travels/', include(travel_pattens, namespace='travels')),
    url(r'^static_data/$', StaticDataView.as_view(), name='static_data'),
    url(r'^permission_matrix/$', PermissionMatrixView.as_view(), name='permission_matrix'),
)
