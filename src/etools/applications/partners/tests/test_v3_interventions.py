import datetime
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.partners.models import Intervention, InterventionManagementBudget, InterventionSupplyItem
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    FileTypeFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    InterventionManagementBudgetFactory,
    InterventionResultLinkFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    LowerResultFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('intervention-list', '', {}),
            ('intervention-detail', '1/', {'pk': 1}),
            ('intervention-accept', '1/accept/', {'pk': 1}),
            ('intervention-accept-review', '1/accept_review/', {'pk': 1}),
            ('intervention-send-partner', '1/send_to_partner/', {'pk': 1}),
            ('intervention-send-unicef', '1/send_to_unicef/', {'pk': 1}),
            ('intervention-budget', '1/budget/', {'intervention_pk': 1}),
            ('intervention-supply-item', '1/supply/', {'intervention_pk': 1}),
            (
                'intervention-supply-item-detail',
                '1/supply/2/',
                {'intervention_pk': 1, 'pk': 2},
            ),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/interventions/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class BaseInterventionTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])
        self.user.groups.add(GroupFactory())
        self.partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
        )


class TestList(BaseInterventionTestCase):
    def test_get(self):
        intervention = InterventionFactory()
        frs = FundsReservationHeaderFactory(
            intervention=intervention,
            currency='USD',
        )
        FundsReservationItemFactory(fund_reservation=frs)
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], intervention.pk)

    def test_list_for_partner(self):
        InterventionFactory()

        intervention = InterventionFactory()
        user = UserFactory(is_staff=False, groups__data=[])
        user_staff_member = PartnerStaffFactory(partner=intervention.agreement.partner, email=user.email)
        user.profile.partner_staff_member = user_staff_member.id
        user.profile.save()

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], intervention.pk)

    def test_not_authenticated(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=AnonymousUser(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_partner_user(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=UserFactory(is_staff=False, groups__data=[]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_interventions_for_empty_result_link(self):
        InterventionResultLinkFactory(cp_output=None)
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_cfei_number(self):
        for _ in range(3):
            InterventionFactory()
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        # set cfei_number value
        cfei_number = "9723495790932423"
        intervention.cfei_number = cfei_number
        intervention.save()
        self.assertEqual(
            Intervention.objects.filter(
                cfei_number__icontains=cfei_number,
            ).count(),
            1,
        )

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={"search": cfei_number[:-5]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class TestCreate(BaseInterventionTestCase):
    def test_post(self):
        data = {
            "document_type": Intervention.PD,
            "title": "PMP Intervention",
            "contingency_pd": True,
            "agreement": self.agreement.pk,
            "reference_number_year": datetime.date.today().year,
            "humanitarian_flag": True,
            "cfei_number": "321",
            "budget_owner": self.user.pk,
        }
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        i = Intervention.objects.get(pk=data.get("id"))
        self.assertTrue(i.humanitarian_flag)
        self.assertTrue(data.get("humanitarian_flag"))
        self.assertEqual(data.get("cfei_number"), "321")
        self.assertEqual(data.get("budget_owner"), self.user.pk)

    def test_add_intervention_by_partner_member(self):
        partner_user = UserFactory(is_staff=False, groups__data=[])
        staff_member = PartnerStaffFactory(email=partner_user.email)
        partner_user.profile.partner_staff_member = staff_member.id
        partner_user.profile.save()
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=partner_user,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_intervention_by_anonymous(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=AnonymousUser(),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_minimal_intervention(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={
                'document_type': Intervention.PD,
                'title': 'My test intervention',
                'agreement': self.agreement.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


class TestManagementBudget(BaseInterventionTestCase):
    def test_get(self):
        intervention = InterventionFactory()
        budget_qs = InterventionManagementBudget.objects.filter(
            intervention=intervention,
        )
        assert not budget_qs.exists()
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertTrue(budget_qs.exists())
        self.assertEqual(data["act1_unicef"], "0.00")
        self.assertEqual(data["act1_partner"], "0.00")
        self.assertEqual(data["act2_unicef"], "0.00")
        self.assertEqual(data["act2_partner"], "0.00")
        self.assertEqual(data["act3_unicef"], "0.00")
        self.assertEqual(data["act3_partner"], "0.00")
        self.assertNotIn('intervention', response.data)

    def test_put(self):
        intervention = InterventionFactory()
        budget_qs = InterventionManagementBudget.objects.filter(
            intervention=intervention,
        )
        assert not budget_qs.exists()
        response = self.forced_auth_req(
            "put",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                "act1_unicef": 1000,
                "act1_partner": 2000,
                "act2_unicef": 3000,
                "act2_partner": 4000,
                "act3_unicef": 5000,
                "act3_partner": 6000,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertTrue(budget_qs.exists())
        self.assertEqual(data["act1_unicef"], "1000.00")
        self.assertEqual(data["act1_partner"], "2000.00")
        self.assertEqual(data["act2_unicef"], "3000.00")
        self.assertEqual(data["act2_partner"], "4000.00")
        self.assertEqual(data["act3_unicef"], "5000.00")
        self.assertEqual(data["act3_partner"], "6000.00")
        self.assertIn('intervention', response.data)

    def test_patch(self):
        intervention = InterventionFactory()
        InterventionManagementBudgetFactory(intervention=intervention)
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={"act1_unicef": 1000},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["act1_unicef"], "1000.00")
        self.assertIn('intervention', response.data)


class TestSupplyItem(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory()

    def test_list(self):
        count = 10
        for __ in range(count):
            InterventionSupplyItemFactory(intervention=self.intervention)
        for __ in range(10):
            InterventionSupplyItemFactory()
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), count)
        self.assertIn('id', response.data[0])

    def test_post(self):
        item_qs = InterventionSupplyItem.objects.filter(
            intervention=self.intervention,
        )
        self.assertFalse(item_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
            data={
                "title": "New Supply Item",
                "unit_number": 10,
                "unit_price": 2,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "20.00")
        self.assertTrue(item_qs.exists())
        item = item_qs.first()
        self.assertEqual(item.intervention, self.intervention)

    def test_get(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "20.00")

    def test_put(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "put",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            data={
                "title": "Change Supply Item",
                "unit_number": 20,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "20.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "40.00")

    def test_patch(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            data={
                "unit_price": 3,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "3.00")
        self.assertEqual(response.data["total_price"], "30.00")

    def test_delete(self):
        item = InterventionSupplyItemFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "delete",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestInterventionUpdate(BaseInterventionTestCase):
    def _test_patch(self, mapping):
        intervention = InterventionFactory()
        data = {}
        for field, value in mapping:
            self.assertNotEqual(getattr(intervention, field), value)
            data[field] = value
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        for field, value in mapping:
            self.assertEqual(getattr(intervention, field), value)

    def test_partner_details(self):
        intervention = InterventionFactory()
        agreement = AgreementFactory()
        focal_1 = PartnerStaffFactory()
        focal_2 = PartnerStaffFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "agreement": agreement.pk,
                "partner_focal_points": [focal_1.pk, focal_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertEqual(intervention.agreement, agreement)
        self.assertListEqual(
            sorted([fp.pk for fp in intervention.partner_focal_points.all()]),
            sorted([focal_1.pk, focal_2.pk]),
        )

    def test_unicef_details(self):
        intervention = InterventionFactory()
        agreement = AgreementFactory()
        focal_1 = UserFactory(is_staff=True)
        focal_2 = UserFactory(is_staff=True)
        budget_owner = UserFactory(is_staff=True)
        office = OfficeFactory()
        section = SectionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "agreement": agreement.pk,
                "document_type": Intervention.PD,
                "unicef_focal_points": [focal_1.pk, focal_2.pk],
                "budget_owner": budget_owner.pk,
                "offices": [office.pk],
                "sections": [section.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertEqual(intervention.agreement, agreement)
        self.assertEqual(intervention.document_type, Intervention.PD)
        self.assertListEqual(list(intervention.offices.all()), [office])
        self.assertListEqual(list(intervention.sections.all()), [section])
        self.assertEqual(intervention.budget_owner, budget_owner)
        self.assertListEqual(
            sorted([i.pk for i in intervention.unicef_focal_points.all()]),
            sorted([focal_1.pk, focal_2.pk]),
        )

    def test_document(self):
        mapping = (
            ("title", "Document title"),
            ("context", "Context"),
            ("implementation_strategy", "Implementation strategy"),
            ("ip_program_contribution", "Non-Contribution from partner"),
        )
        self._test_patch(mapping)

    def test_location(self):
        intervention = InterventionFactory()
        self.assertEqual(list(intervention.flat_locations.all()), [])
        loc1 = LocationFactory()
        loc2 = LocationFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "flat_locations": [loc1.pk, loc2.pk]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertListEqual(
            list(intervention.flat_locations.all()),
            [loc1, loc2],
        )

    def test_gender(self):
        mapping = (
            ("gender_rating", Intervention.RATING_PRINCIPAL),
            ("gender_narrative", "Gender narrative"),
            ("sustainability_rating", Intervention.RATING_PRINCIPAL),
            ("sustainability_narrative", "Sustainability narrative"),
            ("equity_rating", Intervention.RATING_PRINCIPAL),
            ("equity_narrative", "Equity narrative"),
        )
        self._test_patch(mapping)

    def test_miscellaneous(self):
        mapping = (
            ("technical_guidance", "Tech guidance"),
            ("capacity_development", "Capacity dev"),
            ("other_partners_involved", "Other partners"),
            ("other_info", "Other info"),
        )
        self._test_patch(mapping)


class BaseInterventionActionTestCase(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        call_command("update_notifications")

        self.partner_user = UserFactory(is_staff=False, groups__data=[])
        staff_member = PartnerStaffFactory(email=self.partner_user.email)
        self.partner_user.profile.partner_staff_member = staff_member.pk
        self.partner_user.profile.save()
        office = OfficeFactory()
        section = SectionFactory()

        agreement = AgreementFactory(
            partner=staff_member.partner,
            signed_by_unicef_date=datetime.date.today(),
        )
        self.intervention = InterventionFactory(
            agreement=agreement,
            country_programme=agreement.country_programme,
            start=datetime.date.today(),
            end=datetime.date.today() + datetime.timedelta(days=3),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            unicef_signatory=self.user,
            partner_authorized_officer_signatory=staff_member,
        )
        self.intervention.partner_focal_points.add(staff_member)
        self.intervention.unicef_focal_points.add(self.user)
        self.intervention.offices.add(office)
        self.intervention.sections.add(section)
        AttachmentFactory(
            file="sample.pdf",
            object_id=self.intervention.pk,
            content_type=ContentType.objects.get_for_model(self.intervention),
            code="partners_intervention_signed_pd",
        )
        ReportingRequirementFactory(intervention=self.intervention)
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            currency='USD',
        )

        self.notify_path = "etools.applications.partners.views.interventions_v3_actions.send_notification_with_template"


class TestInterventionAccept(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-accept',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        # unicef accepts
        self.assertFalse(self.intervention.unicef_accepted)
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.unicef_accepted)

        # unicef attempt to accept again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("UNICEF has already accepted this PD.", response.data)
        mock_send.assert_not_called()

        # partner accepts
        self.assertFalse(self.intervention.partner_accepted)
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.partner_accepted)

        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Partner has already accepted this PD.", response.data)


class TestInterventionAcceptReview(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-accept-review',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept-review', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-accept-review',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get(self):
        # unicef accepts
        self.assertFalse(self.intervention.unicef_accepted)
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.unicef_accepted)

        # unicef attempt to accept and review again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already in Review status.", response.data)
        mock_send.assert_not_called()


class TestInterventionUnlock(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-unlock',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-unlock', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-unlock', args=[intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.save()

        # unicef unlocks
        self.assertTrue(self.intervention.unicef_accepted)
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertFalse(self.intervention.unicef_accepted)

        # unicef attempt to unlock again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already unlocked.", response.data)
        mock_send.assert_not_called()

        # partner unlocks
        self.assertTrue(self.intervention.partner_accepted)
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertFalse(self.intervention.partner_accepted)

        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already unlocked.", response.data)


class TestInterventionSendToPartner(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-send-partner',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-send-partner', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-send-partner',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        self.assertTrue(self.intervention.unicef_court)

        # unicef sends PD to partner
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()

        # unicef request when PD in partner court
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is currently with Partner", response.data)
        mock_send.assert_not_called()


class TestInterventionSendToUNICEF(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-send-unicef',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-send-unicef', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        self.assertFalse(self.intervention.unicef_court)

        # partner sends PD to unicef
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()

        # partner request when PD in partner court
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is currently with UNICEF", response.data)
        mock_send.assert_not_called()


class TestTimeframesValidation(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(
            start=datetime.date(year=1970, month=1, day=1),
            end=datetime.date(year=1970, month=12, day=31),
        )
        self.result_link = InterventionResultLinkFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
            intervention=self.intervention
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)

        self.activity = InterventionActivityFactory(result=self.pd_output)

    def test_update_start(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=4, day=1),
                end_date=datetime.date(year=1970, month=7, day=1)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'start': datetime.date(year=1970, month=5, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['start'], '1970-05-01')

    def test_update_start_with_active_timeframe(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'start': datetime.date(year=1970, month=5, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('start', response.data)

    def test_update_end_with_active_timeframe(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'end': datetime.date(year=1970, month=10, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('end', response.data)


class TestInterventionAttachments(BaseTenantTestCase):
    def setUp(self):
        self.intervention = InterventionFactory()
        self.unicef_user = UserFactory(is_staff=True, groups__data=['UNICEF User'])
        self.partnership_manager = UserFactory(is_staff=True, groups__data=['Partnership Manager', 'UNICEF User'])
        self.example_attachment = AttachmentFactory(file="test_file.pdf", file_type=None, code="", )
        self.list_url = reverse('pmp_v3:intervention-attachment-list', args=[self.intervention.id])

    def test_list(self):
        response = self.forced_auth_req(
            'get',
            self.list_url,
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_add_attachment(self):
        self.assertEqual(self.intervention.attachments.count(), 0)
        response = self.forced_auth_req(
            'post',
            self.list_url,
            user=self.partnership_manager,
            data={
                "type": FileTypeFactory().pk,
                "attachment_document": self.example_attachment.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.intervention.attachments.count(), 1)
        self.assertIsInstance(response.data['intervention'], dict)

    def test_add_attachment_as_unicef_user(self):
        response = self.forced_auth_req(
            'post',
            self.list_url,
            user=self.unicef_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_remove_attachment(self):
        attachment = InterventionAttachmentFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-attachments-update', args=[self.intervention.id, attachment.id]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
