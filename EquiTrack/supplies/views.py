__author__ = 'jcranwellward'

import os
import csv
import datetime

from django.db.models import F, Sum
from django.views.generic import TemplateView
from django.core.servers.basehttp import FileWrapper

#from django_datatables_view.base_datatable_view import BaseDatatableView

from partners.models import DistributionPlan


class SuppliesDashboardView(TemplateView):

    template_name = 'supplies/dashboard.html'

    def get_context_data(self, **kwargs):
        plans = DistributionPlan.objects.filter(sent=True)
        return {
            'distributions': plans.count(),
            'completed': plans.filter(quantity=F('delivered')).count(),
            'supplies_planned': plans.aggregate(Sum('quantity')).values()[0],
            'supplies_delivered': plans.aggregate(Sum('delivered')).values()[0]
        }


# @login_required
# def send_apk(request):
#
#     filename = os.path.join(settings.STATIC_ROOT, 'app/UniSupply.apk')
#
#     wrapper = FileWrapper(file(filename))
#     response = HttpResponse(wrapper)
#     response['Content-Length'] = os.path.getsize(filename)
#     response['Content-Type'] = 'application/vnd.android.package-archive'
#     response['Content-Disposition'] = 'inline; filename={}'.format('UniSupply.apk')
#     return response
#
#
# class SiteListJson(BaseDatatableView):
#     columns = [
#         '_id',
#         'pcodename',
#         'mohafaza',
#         'district',
#         'cadastral',
#         'municipaliy',
#         'no_tent',
#         'no_ind',
#         'lat',
#         'long',
#         'elevation',
#         'confirmed_ip',
#         'actual_ip',
#         'unicef_priority',
#         'assessment_date',
#         'num_assessments',
#         'completed',
#         'remaining',
#         'distribution_date',
#         '3 months',
#         'Completed 3 months',
#         'Remaining 3 months',
#         '12 months',
#         'Completed 12 months',
#         'Remaining 12 months',
#         '2 years',
#         'Completed 2 years',
#         'Remaining 2 years',
#         '3 years',
#         'Completed 3 years',
#         'Remaining 3 years',
#         '5 years',
#         'Completed 5 years',
#         'Remaining 5 years',
#         '7 years',
#         'Completed 7 years',
#         'Remaining 7 years',
#         '9 years',
#         'Completed 9 years',
#         'Remaining 9 years',
#         '12 years',
#         'Completed 12 years',
#         'Remaining 12 years',
#         '14 years',
#         'Completed 14 years',
#         'Remaining 14 years',
#         'total_kits',
#         'total_completed',
#         'total_remaining',
#     ]
#     order_columns = {
#         'district': 'asc',
#         'pcodename': 'asc',
#         'actual_ip': 'asc',
#         'distribution_date': 'asc'
#     }
#
#     def get_initial_queryset(self):
#         # return queryset used as base for futher sorting/filtering
#         # these are simply objects displayed in datatable
#         # You should not filter data returned here by any filter values entered by user. This is because
#         # we need some base queryset to count total number of records.
#         return winter.manifest.find()
#
#     def filter_queryset(self, qs):
#         # use request parameters to filter queryset
#         #
#         # simple example:
#         search = self.request.POST.get('search[value]', None)
#         if search:
#             qs = qs.filter(name__istartswith=search)
#
#         return qs
#
#     def ordering(self, qs):
#         """ Get parameters from the request and prepare order by clause
#         """
#         order = []
#         for col, direct in self.order_columns.iteritems():
#             sdir = -1 if direct == 'desc' else 1
#             order.append((col, sdir))
#         return qs.sort(order)
#
#     def paging(self, qs):
#         # disable server side paging
#         return qs
#
#     def prepare_results(self, qs):
#         # prepare list with output column data
#         # queryset is already paginated here
#         data = []
#         for row in qs:
#             data.append([row[column] if column in row else '' for column in self.get_columns()])
#         return data
#
#     def get(self, request, *args, **kwargs):
#
#         if request.REQUEST.get('format', 'json') == 'csv':
#
#             rows = self.prepare_results(self.get_initial_queryset())
#             rows.insert(0, self.columns)
#             pseudo_buffer = Echo()
#             writer = csv.writer(pseudo_buffer)
#             response = StreamingHttpResponse(
#                 (writer.writerow([unicode(s).encode("utf-8") for s in row]) for row in rows),
#                 content_type="text/csv")
#             response['Content-Disposition'] = 'attachment; filename="manifest-{}.csv"'.format(
#                 datetime.datetime.now().strftime('%d-%m-%Y')
#             )
#             return response
#
#         return super(SiteListJson, self).get(request, *args, **kwargs)
#
#
# class Echo(object):
#     """An object that implements just the write method of the file-like
#     interface.
#     """
#     def write(self, value):
#         """Write the value by returning it, instead of storing in a buffer."""
#         return value