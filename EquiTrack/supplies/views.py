__author__ = 'jcranwellward'

import os
import csv
import datetime
import sys
from django.db.models import F, Sum
from django.views.generic import TemplateView
from django.core.servers.basehttp import FileWrapper
from django_datatables_view.base_datatable_view import BaseDatatableView
from partners.models import DistributionPlan
from .tasks import initiate_mongo_connection
from django.http.response import StreamingHttpResponse



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


#@login_required
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


class SiteListJson(BaseDatatableView):

    columns = [
        '_id',
        'p_code',
        'p_code_name',
        'phone_number',
        'latitude',
        'longitude',
        'first_name',
        'middle_name',
        'last_name',
        'official_id',
        'id_type',
        'gender',
        'marital_status',
        'dob',
        'creation_date',
        'partner_name',
        'Do you have school-aged children not attending school?',
        'Do you have school aged children working',
        'Is the principle applicant still present?',
        'Will the family move in the near future?',
        'new_location',
        'Under 4 months',
        'Under 24 months',
        '2 years',
        '3 years',
        '4 years',
        '5 years',
        '6 years',
        '7 years',
        '8 years',
        '9 years',
        '10 years',
        '11 years',
        '12 years',
        '13 years',
        '14 years',
        'CSC Survey Q1 - Did you recieve the CSC card?',
        'CSC Survey Q2 - Do you still have the CSC card?',
        'CSC Survey Q3 - Do you remember the PIN number?',
        'CSC Survey Q4 - Please enter the last four digits of the card',
        'CSC Survey Q5 - Is the case number written on the card equal to the one in the registration certificate?',
        'CSC Survey Q6 - Reasons for not having the card',
        'CSC Survey Q7 - Did you inform UNHCR or the Bank?',
        'CSC Survey Q8 - Did UNHCR issue a new PIN number?',
        'CSC Survey Q9 - Input number of actual card',
        'CSC Survey Q10 - Did you inform UNHCR or the Bank?',
        'WFP Survey Q1 - Did you recieve a WFP Food voucher card?',
        'WFP Survey Q2 - Do you still have the WFP voucher card?',
        'WFP Survey Q3 - Please input the last 4 digits of the WFP card',
        'WFP Survey Q4 - Does the case number correspond to the WFP card?',
        'WFP Survey Q5 - Did your WFP voucher Card get upgraded to an ATM Card?',
        'WFP Survey Q6 - Do you still have the PIN number?',
        'WFP Survey Q7 - Is the card still functioning/activated?',
        'WFP Survey Q8 - Reasons for not having the WFP card',
        'WFP Survey Q9 - Did you notify the partner/bank?',
        'WFP Survey Q10 - Take down the card number',
        'WFP Survey Q11 - Did you inform the bank?'
    ]


    order_columns = {
        'district': 'asc',
        'partner_name':'asc',
        'pcodename': 'asc',
    }

    def get_initial_queryset(self):
        # return queryset used as base for futher sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        db = initiate_mongo_connection()
        return db.manifest.find()

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
        order = []
        for col, direct in self.order_columns.iteritems():
            sdir = -1 if direct == 'desc' else 1
            order.append((col, sdir))
        return qs.sort(order)

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