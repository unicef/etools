from threading import active_count

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory, QuestionFactory
from etools.applications.field_monitoring.planning.actions.duplicate_monitoring_activity import \
    DuplicateMonitoringActivity
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory, InterventionFactory, AgreementFactory
from etools.applications.reports.tests.factories import ResultFactory, OfficeFactory, SectionFactory


class TestDuplicateMonitoringActivity(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        partners = [PartnerFactory(organization=OrganizationFactory()), PartnerFactory(organization=OrganizationFactory())]
        interventions = [InterventionFactory(
            agreement=AgreementFactory(partner=partners[0])
        ), InterventionFactory(
            agreement=AgreementFactory(partner=partners[1])
        )]
        self.activity = MonitoringActivityFactory(
            partners=partners,
            status=MonitoringActivity.STATUS_DRAFT,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm,
            location=LocationFactory(),
            location_site=LocationSiteFactory(),
            interventions=interventions,
            cp_outputs=[ResultFactory(), ResultFactory()],
            offices=[OfficeFactory(), OfficeFactory()],
            sections=[SectionFactory(), SectionFactory()],
            team_members=[UserFactory(), UserFactory()],
        )
        ActivityQuestionFactory(
            question=QuestionFactory(),
            monitoring_activity=self.activity
        )
        ActivityQuestionFactory(
            question=QuestionFactory(),
            monitoring_activity=self.activity
        )

    def test_duplicates_activity(self):
        duplicated_activity = DuplicateMonitoringActivity().execute(self.activity.id, with_checklist=False, user=UserFactory())

        self.assertNotEqual(duplicated_activity.id, self.activity.id)
        self.assertEqual(duplicated_activity.status, MonitoringActivity.STATUS_DRAFT)
        self.assertEqual(duplicated_activity.monitor_type, self.activity.monitor_type)
        self.assertEqual(duplicated_activity.location, self.activity.location)
        self.assertEqual(duplicated_activity.location_site, self.activity.location_site)
        self._assert_many_to_many_relations(duplicated_activity)
        self.assertFalse(duplicated_activity.questions.exists())

    def test_duplicates_activity_with_checklist(self):
        duplicated_activity = DuplicateMonitoringActivity().execute(self.activity.id, with_checklist=True, user=UserFactory())

        self.assertNotEqual(duplicated_activity.id, self.activity.id)
        self.assertEqual(duplicated_activity.status, MonitoringActivity.STATUS_CHECKLIST)
        self.assertEqual(duplicated_activity.monitor_type, self.activity.monitor_type)
        self.assertEqual(duplicated_activity.location, self.activity.location)
        self.assertEqual(duplicated_activity.location_site, self.activity.location_site)
        self._assert_many_to_many_relations(duplicated_activity)
        self._assert_activity_questions(duplicated_activity)

    def _assert_many_to_many_relations(self, duplicated_activity):
        self.assertEqual(list(duplicated_activity.partners.order_by("id")), list(self.activity.partners.order_by("id")))
        self.assertEqual(list(duplicated_activity.interventions.order_by("id")),
                         list(self.activity.interventions.order_by("id")))
        self.assertEqual(list(duplicated_activity.cp_outputs.order_by("id")),
                         list(self.activity.cp_outputs.order_by("id")))
        self.assertEqual(list(duplicated_activity.offices.order_by("id")),
                         list(self.activity.offices.order_by("id")))
        self.assertEqual(list(duplicated_activity.sections.order_by("id")),
                         list(self.activity.sections.order_by("id")))
        self.assertEqual(list(duplicated_activity.team_members.order_by("id")),
                         list(self.activity.team_members.order_by("id")))

    def _assert_activity_questions(self, duplicated_activity):
        activity_questions = self.activity.questions.order_by("id").values_list("question_id", flat=True)
        duplicated_activity_questions = duplicated_activity.questions.order_by("id").values_list("question_id", flat=True)
        self.assertEqual(list(activity_questions), list(duplicated_activity_questions))
