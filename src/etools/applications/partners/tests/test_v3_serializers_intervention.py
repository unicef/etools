from unittest.mock import Mock

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import SENIOR_MANAGEMENT_GROUP
from etools.applications.partners.serializers import interventions_v3 as serializers
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestInterventionDetailSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory()
        cls.partner = PartnerFactory()
        cls.partner_staff = cls.partner.staff_members.all().first()
        cls.partner_user = cls.partner_staff.user
        cls.mock_unicef_request = Mock(user=cls.unicef_user)
        cls.mock_partner_request = Mock(user=cls.partner_user)
        cls.unicef_serializer = serializers.InterventionDetailSerializer(
            context={"request": cls.mock_unicef_request},
        )
        cls.partner_serializer = serializers.InterventionDetailSerializer(
            context={"request": cls.mock_partner_request},
        )

    def setUp(self):
        super().setUp()
        self.default_actions = sorted([
            "download_comments",
            "export",
            "generate_pdf",
        ])

    def test_available_actions_not_draft(self):
        pd = InterventionFactory(status=Intervention.SIGNED)
        pd.unicef_focal_points.add(self.unicef_user)
        pd.partner_focal_points.add(self.partner_staff)
        self.assertEqual(pd.status, pd.SIGNED)
        self.assertEqual(
            sorted(self.unicef_serializer.get_available_actions(pd)),
            self.default_actions,
        )
        self.assertEqual(
            sorted(self.partner_serializer.get_available_actions(pd)),
            self.default_actions,
        )

    def test_available_actions_partner_accept(self):
        pd = InterventionFactory(unicef_court=False)
        pd.partner_focal_points.add(self.partner_staff)
        self.assertEqual(pd.status, pd.DRAFT)
        self.assertFalse(pd.partner_accepted)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["accept", "send_to_unicef"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        pd.partner_accepted = True
        pd.save()
        available_actions = self.partner_serializer.get_available_actions(pd)
        self.assertEqual(
            sorted(available_actions),
            sorted(self.default_actions + ["send_to_unicef", "unlock"])
        )

    def test_available_actions_partner_unlock(self):
        pd = InterventionFactory(unicef_court=False, partner_accepted=True)
        pd.partner_focal_points.add(self.partner_staff)
        self.assertEqual(pd.status, pd.DRAFT)
        self.assertTrue(pd.partner_accepted)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "unlock",
            "send_to_unicef",
        ]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_partner_with_unicef(self):
        pd = InterventionFactory(unicef_court=True)
        pd.partner_focal_points.add(self.partner_staff)
        self.assertEqual(pd.status, pd.DRAFT)
        self.assertTrue(pd.unicef_court)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_budget_owner(self):
        pd = InterventionFactory(budget_owner=self.unicef_user)
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "accept",
            "review",
            "signature",
        ]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_management(self):
        pd = InterventionFactory()
        self.unicef_user.groups.add(
            GroupFactory(name=SENIOR_MANAGEMENT_GROUP),
        )
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["cancel"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_unicef(self):
        pd = InterventionFactory()
        pd.unicef_focal_points.add(self.unicef_user)
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "accept",
            "accept_review",
            "cancel",
            "send_to_partner",
            "signature",
        ]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        pd.partner_accepted = True
        pd.save()
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "cancel",
            "send_to_partner",
            "signature",
            "unlock",
        ]
        self.assertEqual(
            sorted(available_actions),
            sorted(expected_actions),
        )

    def _expected_status_list(self, statuses):
        return sorted([
            s for s in Intervention.INTERVENTION_STATUS if s[0] in statuses
        ])

    def test_status_list(self):
        pd = InterventionFactory()
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.DRAFT,
            Intervention.REVIEW,
            Intervention.SIGNATURE,
            Intervention.SIGNED,
            Intervention.ACTIVE,
            Intervention.ENDED,
        ]))

    def test_status_list_suspended(self):
        pd = InterventionFactory(status=Intervention.SUSPENDED)
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.DRAFT,
            Intervention.REVIEW,
            Intervention.SIGNATURE,
            Intervention.SIGNED,
            Intervention.SUSPENDED,
            Intervention.ACTIVE,
            Intervention.ENDED,
        ]))

    def test_status_list_terminated(self):
        pd = InterventionFactory(status=Intervention.TERMINATED)
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.DRAFT,
            Intervention.REVIEW,
            Intervention.SIGNATURE,
            Intervention.SIGNED,
            Intervention.TERMINATED,
        ]))