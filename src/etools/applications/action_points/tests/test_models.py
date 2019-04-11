from django.core.management import call_command
from django.db import connection

from rest_framework.exceptions import ValidationError
from unicef_snapshot.utils import create_dict_with_relations, create_snapshot

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.audit.models import MicroAssessment
from etools.applications.audit.tests.factories import MicroAssessmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.tpm.tests.factories import TPMVisitFactory
from etools.applications.users.tests.factories import UserFactory


class TestActionPointModel(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

    def test_str(self):
        action_point = ActionPointFactory()
        self.assertEqual(str(action_point), '{}/{}/{}/APD'.format(
            connection.tenant.country_short_code or '',
            action_point.created.year, action_point.id
        ))

    def test_complete_fail(self):
        action_point = ActionPointFactory()
        with self.assertRaisesRegex(ValidationError, "comments"):
            action_point.complete()

    def test_complete(self):
        action_point = ActionPointFactory(status='pre_completed')
        action_point.complete()

    def test_completion_date(self):
        action_point = ActionPointFactory(status='pre_completed')
        self.assertIsNone(action_point.date_of_completion)
        action_point.complete()
        action_point.save()
        self.assertIsNotNone(action_point.date_of_completion)

    def test_audit_related(self):
        action_point = ActionPointFactory(engagement=MicroAssessmentFactory())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.audit)

    def test_engagement_subclass(self):
        action_point = ActionPointFactory(engagement=MicroAssessmentFactory())
        self.assertEqual(type(ActionPoint.objects.get(pk=action_point.pk).related_object), MicroAssessment)

    def test_tpm_related(self):
        action_point = ActionPointFactory(tpm_activity=TPMVisitFactory(tpm_activities__count=1).tpm_activities.first())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.tpm)

    def test_t2f_related(self):
        action_point = ActionPointFactory(travel_activity=TravelActivityFactory())
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.t2f)

    def test_not_related(self):
        action_point = ActionPointFactory()
        self.assertEqual(action_point.related_module, ActionPoint.MODULE_CHOICES.apd)

    def test_additional_data(self):
        action_point = ActionPointFactory(status='pre_completed')
        initial_data = create_dict_with_relations(action_point)

        action_point.assigned_to = UserFactory()
        action_point.complete()
        action_point.save()

        author = UserFactory()
        create_snapshot(action_point, initial_data, author)

        self.assertEqual(action_point.history.count(), 1)

        snapshot = action_point.history.first()
        self.assertIn('key_events', snapshot.data)
        self.assertIn(ActionPoint.KEY_EVENTS.status_update, snapshot.data['key_events'])
        self.assertIn(ActionPoint.KEY_EVENTS.reassign, snapshot.data['key_events'])

    def test_audit_related_str(self):
        action_point = ActionPointFactory(engagement=MicroAssessmentFactory())
        self.assertEqual(
            action_point.related_object_str,
            'Micro Assessment {}'.format(action_point.engagement.reference_number)
        )

    def test_tpm_related_str(self):
        action_point = ActionPointFactory(tpm_activity=TPMVisitFactory(tpm_activities__count=1).tpm_activities.first())
        self.assertEqual(
            action_point.related_object_str,
            'Task No 1 for Visit {}'.format(action_point.tpm_activity.tpm_visit.reference_number)
        )

    def test_t2f_related_str(self):
        action_point = ActionPointFactory(travel_activity=TravelActivityFactory())
        self.assertEqual(
            action_point.related_object_str,
            'Task not assigned to Visit'
        )
        action_point.travel_activity.travels.add(TravelFactory(traveler=action_point.travel_activity.primary_traveler))
        self.assertEqual(
            action_point.related_object_str,
            'Task No 1 for Visit {}'.format(action_point.travel_activity.travel.reference_number)
        )
