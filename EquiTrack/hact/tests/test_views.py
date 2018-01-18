from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.urlresolvers import reverse

from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import PartnerFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
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
            rating=PartnerOrganization.RATING_HIGH,
            total_ct_cp=200.0,
            total_ct_cy=150.0
        )
        cls.url = reverse("hact_api:hact-history")

    def setUp(self):
        self.hact_data = [
            ['Implementing Partner', "Partner Name"],
            ['Partner Type', PartnerType.UN_AGENCY],
            ['Shared', "with UNFPA"],
            ['Shared IP', PartnerOrganization.AGENCY_CHOICES.UN],
            ['TOTAL for current CP cycle', "200.00"],
            ['PLANNED for current year', "300.00"],
            ['Current Year (1 Oct - 30 Sep)', "150.00"],
            ['Micro Assessment', "Yes"],
            ['Risk Rating', "High"],
            ['Expiring Threshold', False],
            ['Approach Threshold', False],
            ['Programmatic Visits Planned', 10],
            ['Programmatic Visits M.R', 8],
            ['Programmatic Visits Done', 5],
            ['Spot Checks M.R', 3],
            ['Spot Checks Done', 2],
            ['Audits M.R', 4],
            ['Audits Done', 2],
            ['Flag for Follow up', "No"],
        ]

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
            "Expiring Threshold",
            "Approach Threshold",
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
            "Partner Name",
            PartnerType.UN_AGENCY,
            "with UNFPA",
            PartnerOrganization.AGENCY_CHOICES.UN,
            "200.00",
            "300.00",
            "150.00",
            "Yes",
            "High",
            "False",
            "False",
            "10",  # programmatic visits
            "8",
            "5",
            "3",  # spot checks
            "2",
            "4",  # audits
            "2",
            "No",
        ))

    def test_export_csv_empty_shared_with(self):
        """If partner shared_with value is empty
        make sure we handle that gracefully
        """
        partner = PartnerFactory(
            name="Partner Name",
            partner_type=PartnerType.UN_AGENCY,
            shared_partner="with UNFPA",
            shared_with=None,
            rating="High",
            total_ct_cp=200.0,
            total_ct_cy=150.0
        )
        HactHistoryFactory(
            partner=partner,
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
            "Partner Name",
            PartnerType.UN_AGENCY,
            "with UNFPA",
            PartnerOrganization.AGENCY_CHOICES.UN,
            "200.00",
            "300.00",
            "150.00",
            "Yes",
            "High",
            "False",
            "False",
            "10",  # programmatic visits
            "8",
            "5",
            "3",  # spot checks
            "2",
            "4",  # audits
            "2",
            "No",
        ))
