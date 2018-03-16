from __future__ import absolute_import, division, print_function, unicode_literals

import factory.fuzzy
from rest_framework.exceptions import ValidationError

from EquiTrack.tests.cases import EToolsTenantTestCase
from action_points.tests.factories import ActionPointFactory


class TestActionPointModel(EToolsTenantTestCase):
    def test_str(self):
        action_point = ActionPointFactory()
        self.assertEqual(str(action_point), '{0}/{1}/ACTP'.format(action_point.created.year, action_point.id))

    def test_complete_fail(self):
        action_point = ActionPointFactory()
        with self.assertRaises(ValidationError):
            action_point.complete()

    def test_complete(self):
        action_point = ActionPointFactory()
        action_point.action_taken = factory.fuzzy.FuzzyText()
        action_point.complete()
