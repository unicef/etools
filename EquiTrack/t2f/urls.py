
from django.conf.urls import url, patterns, include

from t2f.views import TravelListViewSet, TravelDetailsViewSet, StaticDataView, PermissionMatrixView, \
    TravelAttachmentViewSet, ActionPointViewSet, InvoiceViewSet, VendorNumberListView, VisionInvoiceExport, \
    VisionInvoiceUpdate

travel_list = TravelListViewSet.as_view({'get': 'list',
                                         'post': 'create'})
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

action_points_list = ActionPointViewSet.as_view({'get': 'list'})
action_points_details = ActionPointViewSet.as_view({'get': 'retrieve',
                                                    'put': 'update',
                                                    'patch': 'partial_update'})

invoices_list = InvoiceViewSet.as_view({'get': 'list'})
invoices_details = InvoiceViewSet.as_view({'get': 'retrieve'})

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
    url(r'^(?P<transition_name>save_and_submit)/$', travel_list_state_change, name='state_change'),
    url(r'^export/$', TravelListViewSet.as_view({'get': 'export'}), name='export'),
    url(r'^finance-export/$', TravelListViewSet.as_view({'get': 'export_finances'}), name='finance_export'),
    url(r'^travel-admin-export/$', TravelListViewSet.as_view({'get': 'export_travel_admins'}),
        name='travel_admin_export'),
    url(r'^invoice-export/$', TravelListViewSet.as_view({'get': 'export_invoices'}), name='invoice_export'),
)


travel_pattens = patterns(
    '',
    url(r'^', include(travel_list_patterns, namespace='list')),
    url(r'^(?P<travel_pk>[0-9]+)/', include(travel_details_patterns, namespace='details')),
)


action_points_patterns = patterns(
    '',
    url(r'^$', action_points_list, name='list'),
    url(r'^(?P<action_point_pk>[0-9]+)/$', action_points_details, name='details'),
)

invoice_patterns = patterns(
    '',
    url(r'^$', invoices_list, name='list'),
    url(r'^(?P<invoice_pk>[0-9]+)/$', invoices_details, name='details'),
)

from t2f.html_views import TravelEditView

urlpatterns = patterns(
    '',
    url(r'^travels/', include(travel_pattens, namespace='travels')),
    url(r'^static_data/$', StaticDataView.as_view(), name='static_data'),
    url(r'^permission_matrix/$', PermissionMatrixView.as_view(), name='permission_matrix'),
    url(r'^action_points/', include(action_points_patterns, namespace='action_points')),
    url(r'^invoices/', include(invoice_patterns, namespace='invoices')),
    url(r'^invoice_calculations/(?P<travel_pk>[0-9]+)/$', TravelEditView.as_view(), name='invedit'),
    url(r'^vendor_numbers/$', VendorNumberListView.as_view(), name='vendor_numbers'),

    # Vision related endpoints
    url(r'^vision_invoice_export/$', VisionInvoiceExport.as_view(), name='vision_invoice_export'),
    url(r'^vision_invoice_update/$', VisionInvoiceUpdate.as_view(), name='vision_invoice_update'),
)
