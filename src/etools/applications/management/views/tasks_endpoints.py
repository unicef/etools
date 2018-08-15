import csv
from abc import ABCMeta
from datetime import date
from functools import partial

from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_restlib.permissions import IsSuperUser

from etools.applications.hact.tasks import update_aggregate_hact_values, update_hact_values
from etools.applications.management.tasks import send_test_email
from etools.applications.partners.tasks import pmp_indicator_report
from etools.applications.users.tasks import user_report


class BasicTaskAPIView(APIView, metaclass=ABCMeta):
    permission_classes = (IsSuperUser,)
    task_function = None
    success_message = 'Task generated Successfully'

    def get(self, request, *args, **kwargs):
        try:
            params = self.request.query_params.copy()
            params['user_email'] = self.request.user.email
            self.task_function.delay(**params)
        except BaseException as e:
            return Response(status=500, data=str(e))

        return Response({'success': self.success_message})


class BasicReportAPIView(APIView, metaclass=ABCMeta):
    permission_classes = (IsSuperUser,)
    report_function = None
    success_message = 'Report generated'
    base_filename = None

    def get(self, request, *args, **kwargs):

        response = HttpResponse(content_type='text/csv')
        filename = self.get_filename()
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = partial(csv.DictWriter, response)
        try:
            params = self.request.query_params.copy()
            self.report_function(writer, **params)
        except BaseException as e:
            return Response(status=500, data=str(e))

        return response

    def get_filename(self):
        today = date.today().strftime("%Y-%b-%d")
        return f'{self.base_filename}_as_of_{today}'


class UpdateHactValuesAPIView(BasicTaskAPIView):
    task_function = update_hact_values
    success_message = 'Task generated Successfully: Update Hact Values'


class UpdateAggregateHactValuesAPIView(BasicTaskAPIView):
    task_function = update_aggregate_hact_values
    success_message = 'Task generated Successfully: Update Aggregate Hact Values'


class TestSendEmailAPIView(BasicTaskAPIView):
    task_function = send_test_email
    success_message = 'Task generated Successfully: Send Test Email'


class UsersReportView(BasicReportAPIView):
    report_function = user_report
    base_filename = 'users'


class PMPIndicatorsReportView(BasicReportAPIView):
    report_function = pmp_indicator_report
    base_filename = 'pmp_indicators'
