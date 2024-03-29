import datetime
from unittest import skip

from django.urls import reverse

from rest_framework import status
from tablib.core import Dataset

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import AgreementAmendmentFactory, AgreementFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import UserFactory


class BaseAgreementModelExportTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.GOVERNMENT,
                cso_type="International",
                vendor_number='Vendor No',
                short_name="Short Name",
            ),
            alternate_name="Alternate Name",
            shared_with=["DPKO", "ECA"],
            address="Address 123",
            phone_number="Phone no 1234567",
            email="email@address.com",
            rating="High",
            core_values_assessment_date=datetime.date.today(),
            total_ct_cp=10000,
            total_ct_cy=20000,
            deleted_flag=False,
            blocked=False,
            type_of_assessment="Type of Assessment",
            last_assessment_date=datetime.date.today(),
        )
        partnerstaff = UserFactory(
            profile__organization=partner.organization,
            realms__data=['IP Viewer']
        )
        cls.agreement = AgreementFactory(
            partner=partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement="fake_attachment.pdf",
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=cls.unicef_staff,
            signed_by_partner_date=datetime.date.today(),
            terms_acknowledged_by=cls.unicef_staff,
        )
        cls.agreement.authorized_officers.add(partnerstaff)
        cls.agreement.save()


class TestAgreementModelExport(BaseAgreementModelExportTestCase):

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Reference Number',
            'Status',
            'Partner Name',
            'Partner Number',
            'Agreement Type',
            'Start Date',
            'End Date',
            'Signed By Partner',
            'Signed By Partner Date',
            'Signed By UNICEF',
            'Signed By UNICEF Date',
            'Partner Authorized Officer',
            'Amendments',
            'URL',
            'Special Conditions PCA',
            'Terms Acknowledged By',
        ])

        exported_agreement = dataset[0]
        self.assertEqual(exported_agreement, (
            self.agreement.agreement_number,
            str(self.agreement.status),
            str(self.agreement.partner.name),
            str(self.agreement.partner.vendor_number),
            self.agreement.agreement_type,
            '{}'.format(self.agreement.start),
            '{}'.format(self.agreement.end),
            '',
            '{}'.format(self.agreement.signed_by_partner_date),
            self.unicef_staff.get_full_name(),
            '{}'.format(self.agreement.signed_by_unicef_date),
            ', '.join([sm.get_full_name() for sm in self.agreement.authorized_officers.all()]),
            '',
            'https://testserver/pmp/agreements/{}/details/'.format(self.agreement.id),
            'No',
            self.unicef_staff.get_full_name(),
        ))

    @skip('TODO REALMS unskip once old_partner_manager FK field is removed')
    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 28)
        self.assertEqual(len(dataset[0]), 28)

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAgreementAmendmentModelExport(BaseAgreementModelExportTestCase):
    def setUp(self):
        super().setUp()
        self.amendment = AgreementAmendmentFactory(
            agreement=self.agreement,
            signed_amendment="fake_attachment.pdf",
            signed_date=datetime.date.today(),
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-amendment-list'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-amendment-list'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 9)
        self.assertEqual(len(dataset[0]), 9)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-amendment-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 10)
        self.assertEqual(len(dataset[0]), 10)
