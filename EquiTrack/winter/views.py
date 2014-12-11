__author__ = 'jcranwellward'

import os
import csv
import datetime

from django.conf import settings
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.core.servers.basehttp import FileWrapper

from django_datatables_view.base_datatable_view import BaseDatatableView

from .tasks import winter


class WinterDashboardView(TemplateView):

    template_name = 'winter/dashboard.html'

    def get_context_data(self, **kwargs):
        return {
            'assessed': winter.data.find({'type': 'assessment'}).count(),
            'completed': winter.data.find({'type': 'assessment', 'completed': True}).count()
        }


@login_required
def send_apk(request):

    filename = os.path.join(settings.STATIC_ROOT, 'app/UniSupply.apk')

    wrapper = FileWrapper(file(filename))
    response = HttpResponse(wrapper)
    response['Content-Length'] = os.path.getsize(filename)
    response['Content-Type'] = 'application/vnd.android.package-archive'
    response['Content-Disposition'] = 'inline; filename={}'.format('UniSupply.apk')
    return response


class SiteListJson(BaseDatatableView):
    columns = [
        '_id',
        'pcodename',
        'mohafaza',
        'district',
        'cadastral',
        'municipaliy',
        'no_tent',
        'no_ind',
        'lat',
        'long',
        'elevation',
        'confirmed_ip',
        'unicef_priority',
        'assessment_date',
        'num_assessments',
        'completed',
        '3 months',
        '12 months',
        '2 years',
        '3 years',
        '5 years',
        '7 years',
        '9 years',
        '12 years',
        '14 years',
        'total_kits',
    ]
    order_columns = columns

    def get_initial_queryset(self):
        # return queryset used as base for futher sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        return winter.manifest.find()

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        #
        # simple example:
        search = self.request.POST.get('search[value]', None)
        if search:
            qs = qs.filter(name__istartswith=search)

        return qs

    def ordering(self, qs):
        """ Get parameters from the request and prepare order by clause
        """
        request = self.request

        # Number of columns that are used in sorting
        sorting_cols = 0
        if self.pre_camel_case_notation:
            try:
                sorting_cols = int(request.REQUEST.get('iSortingCols', 0))
            except ValueError:
                sorting_cols = 0
        else:
            sort_key = 'order[{0}][column]'.format(sorting_cols)
            while sort_key in self.request.REQUEST:
                sorting_cols += 1
                sort_key = 'order[{0}][column]'.format(sorting_cols)

        order = []
        order_columns = self.get_order_columns()

        for i in range(sorting_cols):
            # sorting column
            sort_dir = 'asc'
            try:
                if self.pre_camel_case_notation:
                    sort_col = int(request.REQUEST.get('iSortCol_{0}'.format(i)))
                    # sorting order
                    sort_dir = request.REQUEST.get('sSortDir_{0}'.format(i))
                else:
                    sort_col = int(request.REQUEST.get('order[{0}][column]'.format(i)))
                    # sorting order
                    sort_dir = request.REQUEST.get('order[{0}][dir]'.format(i))
            except ValueError:
                sort_col = 0

            sdir = -1 if sort_dir == 'desc' else 1
            sortcol = order_columns[sort_col]

            if isinstance(sortcol, list):
                for sc in sortcol:
                    order.append((sc, sdir))
            else:
                order.append((sortcol, sdir))

        if order:
            return qs.sort(order)
        return qs

    def paging(self, qs):
        # disable server side paging
        return qs

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        data = []
        for row in qs:
            data.append([row[column] if column in row else '' for column in self.get_columns()])
        return data

    def get(self, request, *args, **kwargs):

        if request.REQUEST.get('format', 'json') == 'csv':

            rows = self.prepare_results(self.get_initial_queryset())
            rows.insert(0, self.columns)
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            response = StreamingHttpResponse(
                (writer.writerow([unicode(s).encode("utf-8") for s in row]) for row in rows),
                content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename="manifest-{}.csv"'.format(
                datetime.datetime.now().strftime('%d-%m-%Y')
            )
            return response

        return super(SiteListJson, self).get(request, *args, **kwargs)


class Echo(object):
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value