from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.urlresolvers import reverse
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.tests.mixins import APITenantTestCase
from EquiTrack.factories import PartnerFactory, UserFactory
from hact.tests.factories import HactHistoryFactory
from partners.models import PartnerOrganization, PartnerType


class TestHactHistoryAPIView(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            name="Partner Name",
            partner_type=PartnerType.UN_AGENCY,
            shared_partner="with UNFPA",
            shared_with=[PartnerOrganization.AGENCY_CHOICES.UN],
            rating="High",
            total_ct_cp=200.0,
            total_ct_cy=150.0
        )
        cls.url = reverse("hact_api:hact-history")

    def setUp(self):
        self.hact_data = {
            "planned_cash_transfer": 300.0,
            "micro_assessment_needed": "Yes",
            "programmatic_visits": {
                "planned": {"total": 10},
                "required": {"total": 8},
                "completed": {"total": 5},
            },
            "spot_checks": {
                "required": {"total": 3},
                "completed": {"total": 2},
            },
            "audits": {
                "required": 4,
                "completed": 2,
            },
            "follow_up_flags": "No",
        }

    def test_get(self):
        history = HactHistoryFactory(
            partner=self.partner,
            year=2017,
            partner_values=self.hact_data
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], history.pk)
        self.assertEqual(data["partner_values"], self.hact_data)

    def test_filter_year(self):
        history = HactHistoryFactory(
            partner=self.partner,
            year=2017,
            partner_values=self.hact_data,
        )
        HactHistoryFactory(
            partner=self.partner,
            year=2018,
            partner_values=self.hact_data,
        )
        HactHistoryFactory(
            partner=self.partner,
            year=2016,
            partner_values=self.hact_data,
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_user,
            data={"year": 2017}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], history.pk)
        self.assertEqual(data["partner_values"], self.hact_data)

    def test_export_csv(self):
        HactHistoryFactory(
            partner=self.partner,
            year=2017,
            partner_values=self.hact_data
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_user,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, "csv")
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Implementing Partner",
            "Partner Type",
            "Shared",
            "Shared IP",
            "TOTAL for current CP cycle",
            "PLANNED for current year",
            "Current Year (1 Oct - 30 Sep)",
            "Micro Assessment",
            "Risk Rating",
            "Programmatic Visits Planned",
            "Programmatic Visits M.R",
            "Programmatic Visits Done",
            "Spot Checks M.R",
            "Spot Checks Done",
            "Audits M.R",
            "Audits Done",
            "Flag for Follow up",
        ])
        self.assertEqual(dataset[0], (
            self.partner.name,
            self.partner.partner_type,
            self.partner.shared_partner,
            ", ".join(self.partner.shared_with),
            "{:.2f}".format(self.partner.total_ct_cp),
            "300.00",
            "{:.2f}".format(self.partner.total_ct_cy),
            "Yes",
            self.partner.rating,
            "10",  # programmatic visits
            "8",
            "5",
            "3",  # spot checks
            "2",
            "4",  # audits
            "2",
            "No",
        ))

    def test_export_csv_key_errors(self):
        self.hact_data = {"planned_cash_transfer": "wrong"}
        HactHistoryFactory(
            partner=self.partner,
            year=2017,
            partner_values=self.hact_data
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_user,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, "csv")
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset[0], (
            self.partner.name,
            self.partner.partner_type,
            self.partner.shared_partner,
            ", ".join(self.partner.shared_with),
            "{:.2f}".format(self.partner.total_ct_cp),
            "wrong",
            "{:.2f}".format(self.partner.total_ct_cy),
            "",
            self.partner.rating,
            "",  # programmatic visits
            "",
            "",
            "",  # spot checks
            "",
            "",  # audits
            "",
            "",
        ))
