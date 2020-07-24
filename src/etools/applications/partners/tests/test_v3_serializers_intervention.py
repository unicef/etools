from unittest.mock import Mock

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.serializers import interventions_v3 as serializers
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestInterventionDetailSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory()
        cls.partner = PartnerFactory()
        cls.partner_staff = cls.partner.staff_members.all().first()
        cls.partner_user = UserFactory(email=cls.partner_staff.email)
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

    def test_available_actions_not_development(self):
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
        self.assertEqual(pd.status, pd.DEVELOPMENT)
        self.assertFalse(pd.partner_accepted)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["accept"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        pd.partner_accepted = True
        pd.save()
        available_actions = self.partner_serializer.get_available_actions(pd)
        self.assertEqual(sorted(available_actions), self.default_actions)

    def test_available_actions_partner_unlock(self):
        pd = InterventionFactory(unicef_court=False, unicef_accepted=True)
        pd.partner_focal_points.add(self.partner_staff)
        self.assertEqual(pd.status, pd.DEVELOPMENT)
        self.assertTrue(pd.unicef_accepted)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["accept", "unlock"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_budget_owner(self):
        pd = InterventionFactory(budget_owner=self.unicef_user)
        self.assertEqual(pd.status, pd.DEVELOPMENT)
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
            GroupFactory(name='Senior Management Team'),
        )
        self.assertEqual(pd.status, pd.DEVELOPMENT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["cancel"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_unicef(self):
        pd = InterventionFactory()
        pd.unicef_focal_points.add(self.unicef_user)
        self.assertEqual(pd.status, pd.DEVELOPMENT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "accept",
            "cancel",
            "send_to_partner",
            "signature",
        ]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        pd.partner_accepted = True
        pd.save()
        expected_actions += ["unlock", "accept_and_review"]
        available_actions = self.unicef_serializer.get_available_actions(pd)
        self.assertEqual(sorted(available_actions), sorted(expected_actions))
