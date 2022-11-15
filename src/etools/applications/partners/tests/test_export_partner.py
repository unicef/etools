import datetime

from django.urls import reverse

from rest_framework import status
from tablib.core import Dataset

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import AssessmentFactory, PartnerFactory, PartnerPlannedVisitsFactory
from etools.applications.users.tests.factories import UserFactory


class PartnerModelExportTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.UN_AGENCY,
                vendor_number='Vendor No',
                short_name="Short Name"
            ),
            alternate_name="Alternate Name",
            shared_with=["DPKO", "ECA"],
            address="Address 123",
            phone_number="Phone no 1234567",
            email="email@example.com",
            rating="High",
            core_values_assessment_date=datetime.date.today(),
            total_ct_cp=10000,
            total_ct_cy=20000,
            total_ct_ytd=30000,
            deleted_flag=False,
            blocked=False,
            type_of_assessment="Type of Assessment",
            last_assessment_date=datetime.date.today(),
            hact_values={
                "outstanding_findings": 0,
                "audits": {
                    "completed": 0,
                    "minimum_requirements": 0
                },
                "programmatic_visits": {
                    "completed": {
                        "q1": 0,
                        "total": 0,
                        "q3": 0,
                        "q2": 0,
                        "q4": 0
                    },
                    "planned": {
                        "q1": 0,
                        "total": 0,
                        "q3": 0,
                        "q2": 0,
                        "q4": 0
                    }
                },
                "spot_checks": {
                    "completed": {
                        "q1": 0,
                        "total": 0,
                        "q3": 0,
                        "q2": 0,
                        "q4": 0
                    },
                    "planned": {
                        "q1": 0,
                        "total": 0,
                        "q3": 0,
                        "q2": 0,
                        "q4": 0
                    },
                    "follow_up_required": 0
                }
            },
        )
        cls.partnerstaff = UserFactory(
            profile__organization=cls.partner.organization,
            realms__data=['IP Viewer']
        )
        cls.partnerstaff2 = UserFactory(
            profile__organization=cls.partner.organization,
            realms__data=['IP Editor']
        )
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
        dataset = Dataset().load(response.content.decode('utf-8-sig'), 'csv')
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
            'HACT Risk Rating',
            'SEA Risk Rating',
            'Last PSEA Assess. Date',
            'Highest Risk Rating Type',
            'Highest Risk Rating Name',
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
        test_option = [e for e in dataset if e[0] == f'\ufeff{self.partner.vendor_number}'][0]

        # the order of staff members in the results is hard to determine
        # so just ensuring that all relevant staff members are in the results
        for sm in self.partner.staff_members.filter(is_active=True).all():
            member = "{} ({})".format(sm.get_full_name(), sm.email)
            self.assertIn(member, test_option[22])

        self.assertEqual(test_option, (
            f'\ufeff{self.partner.vendor_number}',
            str(self.partner.name),
            self.partner.short_name,
            self.partner.alternate_name,
            "{}".format(self.partner.partner_type),
            ', '.join([x for x in self.partner.shared_with]),
            self.partner.address,
            self.partner.phone_number,
            self.partner.email,
            self.partner.rating,
            '',
            '',
            '',
            '',
            '{}'.format(self.partner.core_values_assessment_date),
            '{:.2f}'.format(self.partner.total_ct_cp),
            '{:.2f}'.format(self.partner.total_ct_ytd),
            deleted_flag,
            blocked,
            self.partner.type_of_assessment,
            '{}'.format(self.partner.last_assessment_date),
            '',
            test_option[22],
            'https://testserver/pmp/partners/{}/details/'.format(self.partner.id),
            '{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
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
        self.assertEqual(len(dataset._get_headers()), 55)
        self.assertEqual(len(dataset[0]), 55)

    def test_csv_flat_export_api_hact_value_string(self):
        partner = self.partner
        partner.pk = None
        organization = OrganizationFactory(vendor_number="Vendor New Num")
        partner.organization = organization
        partner.hact_values = {"key": "random string"}
        partner.save()
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(len(dataset._get_headers()), 55)
        self.assertEqual(len(dataset[0]), 55)

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
        self.assertEqual(len(dataset._get_headers()), 55)
        self.assertEqual(len(dataset[0]), 55)


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
        self.assertEqual(len(dataset._get_headers()), 12)
        self.assertEqual(len(dataset[0]), 12)


class TestPartnerOrganizationAssessmentModelExport(PartnerModelExportTestCase):
    def setUp(self):
        super().setUp()
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
        self.assertEqual(len(dataset._get_headers()), 18)
        self.assertEqual(len(dataset[0]), 18)

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
