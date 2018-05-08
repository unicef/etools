
from django.core.management import call_command

import factory.fuzzy
from rest_framework.exceptions import ValidationError

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.audit.tests.factories import MicroAssessmentFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.snapshot.utils import create_dict_with_relations, create_snapshot
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.tpm.tests.factories import TPMVisitFactory
from etools.applications.users.tests.factories import UserFactory


class TestActionPointModel(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

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

    def test_audit_related(self):
        action_point = ActionPointFactory(engagement=MicroAssessmentFactory())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.audit)

    def test_tpm_related(self):
        action_point = ActionPointFactory(tpm_activity=TPMVisitFactory(tpm_activities__count=1).tpm_activities.first())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.tpm)

    def test_t2f_related(self):
        action_point = ActionPointFactory(travel_activity=TravelFactory().activities.first())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.t2f)

    def test_none_related(self):
        action_point = ActionPointFactory()
        self.assertEqual(action_point.related_module, None)

    def test_additional_data(self):
        action_point = ActionPointFactory()
        initial_data = create_dict_with_relations(action_point)

        action_point.assigned_to = UserFactory()
        action_point.action_taken = factory.fuzzy.FuzzyText().fuzz()
        action_point.complete()
        action_point.save()

        author = UserFactory()
        create_snapshot(action_point, initial_data, author)

        self.assertEqual(action_point.history.count(), 1)

        snapshot = action_point.history.first()
        self.assertIn('key_events', snapshot.data)
        self.assertIn(ActionPoint.KEY_EVENTS.status_update, snapshot.data['key_events'])
        self.assertIn(ActionPoint.KEY_EVENTS.reassign, snapshot.data['key_events'])
