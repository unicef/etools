from unittest.mock import Mock

from django.db import connection

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, PRC_SECRETARY, UNICEF_USER
from etools.applications.partners.serializers import interventions_v3 as serializers
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory


class TestInterventionDetailSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory()
        cls.prc_secretary = UserFactory(
            is_staff=True,
            realms__data=[UNICEF_USER, PRC_SECRETARY],
        )
        cls.partner = PartnerFactory()
        cls.partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.partner.organization
        )
        cls.mock_unicef_request = Mock(user=cls.unicef_user)
        cls.mock_prc_secretary_request = Mock(user=cls.prc_secretary)
        cls.mock_partner_request = Mock(user=cls.partner_user)
        cls.unicef_serializer = serializers.InterventionDetailSerializer(
            context={"request": cls.mock_unicef_request},
        )
        cls.prc_secretary_serializer = serializers.InterventionDetailSerializer(
            context={"request": cls.mock_prc_secretary_request},
        )
        cls.partner_serializer = serializers.InterventionDetailSerializer(
            context={"request": cls.mock_partner_request},
        )

    def setUp(self):
        super().setUp()
        self.default_actions = sorted([
            "download_comments",
            "export_results",
            "export_pdf",
            "export_xls",
        ])

    def test_available_actions_not_draft(self):
        pd = InterventionFactory(status=Intervention.SIGNED)
        pd.unicef_focal_points.add(self.unicef_user)
        pd.partner_focal_points.add(self.partner_user)
        self.assertEqual(pd.status, pd.SIGNED)
        self.assertEqual(
            sorted(self.unicef_serializer.get_available_actions(pd)),
            self.default_actions + ['suspend', 'terminate'],
        )
        self.assertEqual(
            sorted(self.partner_serializer.get_available_actions(pd)),
            self.default_actions,
        )

    def test_available_actions_partner_accept(self):
        pd = InterventionFactory(unicef_court=False)
        pd.partner_focal_points.add(self.partner_user)
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
        pd.partner_focal_points.add(self.partner_user)
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
        pd.partner_focal_points.add(self.partner_user)
        self.assertEqual(pd.status, pd.DRAFT)
        self.assertTrue(pd.unicef_court)
        available_actions = self.partner_serializer.get_available_actions(pd)
        expected_actions = self.default_actions
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_budget_owner(self):
        pd = InterventionFactory(budget_owner=self.unicef_user)
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["accept", "send_to_partner", "accept_on_behalf_of_partner"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_prc_secretary(self):
        pd = InterventionFactory()
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.prc_secretary_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ["cancel"]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_management(self):
        pd = InterventionFactory()
        RealmFactory(
            user=self.unicef_user,
            organization=self.partner.organization,
            country=connection.tenant,
            group=GroupFactory(name=PARTNERSHIP_MANAGER_GROUP)
        )
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_focal_point(self):
        pd = InterventionFactory()
        pd.unicef_focal_points.add(self.unicef_user)
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + ['accept_on_behalf_of_partner', 'send_to_partner']
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_management_unsuspend(self):
        pd = InterventionFactory(status=Intervention.SUSPENDED)
        RealmFactory(
            user=self.unicef_user,
            organization=self.partner.organization,
            country=connection.tenant,
            group=GroupFactory(name=PARTNERSHIP_MANAGER_GROUP)
        )
        self.assertEqual(pd.status, pd.SUSPENDED)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

    def test_available_actions_management_terminate(self):
        pd = InterventionFactory(status=Intervention.ACTIVE)
        RealmFactory(
            user=self.unicef_user,
            organization=self.partner.organization,
            country=connection.tenant,
            group=GroupFactory(name=PARTNERSHIP_MANAGER_GROUP)
        )
        self.assertEqual(pd.status, pd.ACTIVE)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        # not available if closed
        for status in [
                Intervention.CLOSED,
                Intervention.ENDED,
                Intervention.TERMINATED,
        ]:
            pd.status = status
            pd.save()
            available_actions = self.unicef_serializer.get_available_actions(pd)
            self.assertNotIn("terminate", available_actions)

    def test_available_actions_unicef(self):
        pd = InterventionFactory()
        pd.unicef_focal_points.add(self.unicef_user)
        self.assertEqual(pd.status, pd.DRAFT)
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
            "accept_on_behalf_of_partner",
            "send_to_partner",
        ]
        self.assertEqual(sorted(available_actions), sorted(expected_actions))

        pd.partner_accepted = True
        pd.save()
        available_actions = self.unicef_serializer.get_available_actions(pd)
        expected_actions = self.default_actions + [
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
        ]))

    def test_status_list_suspended(self):
        pd = InterventionFactory(status=Intervention.SUSPENDED)
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.SUSPENDED,
        ]))

    def test_status_list_terminated(self):
        pd = InterventionFactory(status=Intervention.TERMINATED)
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.TERMINATED,
        ]))

    def test_status_list_cancelled(self):
        pd = InterventionFactory(status=Intervention.CANCELLED)
        status_list = self.unicef_serializer.get_status_list(pd)
        self.assertEqual(sorted(status_list), self._expected_status_list([
            Intervention.CANCELLED,
        ]))
