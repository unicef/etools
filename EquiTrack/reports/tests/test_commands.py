from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management import call_command

from EquiTrack.tests.cases import EToolsTenantTestCase
from reports.models import ResultType


class TestResultTypeCommand(EToolsTenantTestCase):

    def test_command(self):
        self.assertEqual(ResultType.objects.count(), 0)
        call_command('init-result-type')
        self.assertEqual(ResultType.objects.count(), 3)
