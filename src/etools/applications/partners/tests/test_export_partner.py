import datetime

from django.urls import reverse
from django.utils import six

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import (AssessmentFactory, PartnerFactory,
                                                          PartnerPlannedVisitsFactory, PartnerStaffFactory,)
from etools.applications.users.tests.factories import UserFactory


class PartnerModelExportTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            partner_type=PartnerType.UN_AGENCY,
            vendor_number='Vendor No',
            short_name="Short Name",
            alternate_name="Alternate Name",
            shared_with=["DPKO", "ECA"],
            address="Address 123",
            phone_number="Phone no 1234567",
            email="email@example.com",
            rating="High",
            core_values_assessment_date=datetime.date.today(),
            total_ct_cp=10000,
            total_ct_cy=20000,
            deleted_flag=False,
            blocked=False,
            type_of_assessment="Type of Assessment",
            last_assessment_date=datetime.date.today(),
        )
        cls.partnerstaff = PartnerStaffFactory(partner=cls.partner)
        cls.planned_visit = PartnerPlannedVisitsFactory(partner=cls.partner)


class TestPartnerOrganizationModelExport(PartnerModelExportTestCase):
    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Vendor Number',
            'Organizations Full Name',
            'Short Name',
            'Alternate Name',
            'Partner Type',
            'Shared Partner',
            'Address',
            'Phone Number',
            'Email Address',
            'Risk Rating',
            'Date Last Assessed Against Core Values',
            'Actual Cash Transfer for CP (USD)',
            'Actual Cash Transfer for Current Year (USD)',
            'Marked for Deletion',
            'Blocked',
            'Assessment Type',
            'Date Assessed',
            'Assessment Type (Date Assessed)',
            'Staff Members',
            'URL',
            'Planned Programmatic Visits'
        ])
        deleted_flag = "Yes" if self.partner.deleted_flag else "No"
        blocked = "Yes" if self.partner.blocked else "No"

        test_option = [e for e in dataset if e[0] == self.partner.vendor_number][0]

        # the order of staff members in the results is hard to determine
        # so just ensuring that all relevant staff members are in the results
        for sm in self.partner.staff_members.filter(active=True).all():
            member = "{} ({})".format(sm.get_full_name(), sm.email)
            self.assertIn(member, test_option[18])

        self.assertEqual(test_option, (
            self.partner.vendor_number,
            six.text_type(self.partner.name),
            self.partner.short_name,
            self.partner.alternate_name,
            "{}".format(self.partner.partner_type),
            u', '.join([x for x in self.partner.shared_with]),
            self.partner.address,
            self.partner.phone_number,
            self.partner.email,
            self.partner.rating,
            u'{}'.format(self.partner.core_values_assessment_date),
            u'{:.2f}'.format(self.partner.total_ct_cp),
            u'{:.2f}'.format(self.partner.total_ct_cy),
            deleted_flag,
            blocked,
            self.partner.type_of_assessment,
            u'{}'.format(self.partner.last_assessment_date),
            u'',
            test_option[18],
            u'https://testserver/pmp/partners/{}/details/'.format(self.partner.id),
            u'{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
                self.planned_visit.year,
                self.planned_visit.programmatic_q1,
                self.planned_visit.programmatic_q2,
                self.planned_visit.programmatic_q3,
                self.planned_visit.programmatic_q4,
            ),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 47)
        self.assertEqual(len(dataset[0]), 47)

    def test_csv_flat_export_api_hidden(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat", "hidden": True},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 47)
        self.assertEqual(len(dataset[0]), 47)


class TestPartnerStaffMemberModelExport(PartnerModelExportTestCase):
    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-staff-members-list', args=[self.partner.pk]),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-staff-members-list', args=[self.partner.pk]),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(len(dataset._get_headers()), 10)
        self.assertEqual(len(dataset[0]), 10)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-staff-members-list', args=[self.partner.pk]),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(len(dataset._get_headers()), 11)
        self.assertEqual(len(dataset[0]), 11)


class TestPartnerOrganizationAssessmentModelExport(PartnerModelExportTestCase):
    def setUp(self):
        super(TestPartnerOrganizationAssessmentModelExport, self).setUp()
        self.assessment = AssessmentFactory(
            partner=self.partner,
            report="fake_report.pdf"
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-assessment'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-assessment'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 17)
        self.assertEqual(len(dataset[0]), 17)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-assessment'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        headers = dataset._get_headers()
        self.assertEqual(len(headers), 15)
        self.assertIn("Country", headers)
        self.assertEqual(len(dataset[0]), 15)


class TestPartnerOrganizationHactExport(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("partners_api:partner-hact")
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            total_ct_cp=10.00,
            total_ct_cy=8.00,
        )

    def test_csv_export(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 33)
        self.assertEqual(len(dataset[0]), 33)

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
