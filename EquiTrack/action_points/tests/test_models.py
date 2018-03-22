from __future__ import absolute_import, division, print_function, unicode_literals

import factory.fuzzy
from rest_framework.exceptions import ValidationError

from EquiTrack.tests.cases import BaseTenantTestCase
from action_points.models import ActionPoint
from action_points.tests.factories import ActionPointFactory
from audit.tests.factories import MicroAssessmentFactory


class TestActionPointModel(BaseTenantTestCase):
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

    def test_related_module_none_allowed(self):
        action_point = ActionPointFactory(related_module=None)
        self.assertIsNone(action_point.related_module)

    def test_related_module_str(self):
        action_point = ActionPointFactory(related_module=ActionPoint.MODULE_CHOICES.audit)
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.audit)

    def test_related_module_from_related_object(self):
        action_point = ActionPointFactory(
            related_module=None,
            related_object=MicroAssessmentFactory()
        )
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.audit)
