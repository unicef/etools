from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.EquiTrack.permissions import IsSuperUser
from etools.applications.hact.tasks import update_aggregate_hact_values, update_hact_values
from etools.applications.management.tasks import send_test_email


class BasicTaskAPIView(APIView):
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


class UpdateHactValuesAPIView(BasicTaskAPIView):
    task_function = update_hact_values
    success_message = 'Task generated Successfully: Update Hact Values'


class UpdateAggregateHactValuesAPIView(BasicTaskAPIView):
    task_function = update_aggregate_hact_values
    success_message = 'Task generated Successfully: Update Aggregate Hact Values'


class TestSendEmailAPIView(BasicTaskAPIView):
    task_function = send_test_email
    success_message = 'Task generated Successfully: Send Test Email'
