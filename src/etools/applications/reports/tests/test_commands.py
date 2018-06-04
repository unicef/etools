
from django.core.management import call_command

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.reports.models import ResultType


class TestResultTypeCommand(BaseTenantTestCase):

    def test_command(self):
        self.assertEqual(ResultType.objects.count(), 0)
        call_command('init-result-type')
        self.assertEqual(ResultType.objects.count(), 3)
