from __future__ import unicode_literals

import datetime

from django.core.urlresolvers import reverse
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    CountryProgrammeFactory,
    PartnerFactory,
    PartnerStaffFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase


class BaseAgreementModelExportTestCase(APITenantTestCase):
    def setUp(self):
        super(BaseAgreementModelExportTestCase, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        partner = PartnerFactory(
            partner_type='Government',
            vendor_number='Vendor No',
            short_name="Short Name",
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
        partnerstaff = PartnerStaffFactory(partner=partner)
        self.agreement = AgreementFactory(
            partner=partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement="fake_attachment.pdf",
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=self.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        self.agreement.authorized_officers.add(partnerstaff)
        self.agreement.save()


class TestAgreementModelExport(BaseAgreementModelExportTestCase):

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Reference Number',
            'Status',
            'Partner Name',
            'Agreement Type',
            'Start Date',
            'End Date',
            'Signed By Partner',
            'Signed By Partner Date',
            'Signed By UNICEF',
            'Signed By UNICEF Date',
            'Partner Authorized Officer',
            'Amendments',
            'URL'
        ])

        exported_agreement = dataset[0]
        self.assertEqual(exported_agreement, (
            self.agreement.agreement_number,
            unicode(self.agreement.status),
            unicode(self.agreement.partner.name),
            self.agreement.agreement_type,
            '{}'.format(self.agreement.start),
            '{}'.format(self.agreement.end),
            u'',
            '{}'.format(self.agreement.signed_by_partner_date),
            u'',
            '{}'.format(self.agreement.signed_by_unicef_date),
            ', '.join([sm.get_full_name() for sm in self.agreement.authorized_officers.all()]),
            u'',
            u'https://testserver/pmp/agreements/{}/details/'.format(self.agreement.id)
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Id',
            'Reference Number',
            'Attached Agreement',
            'Status',
            'Partner Name',
            'Agreement Type',
            'Start Date',
            'End Date',
            'Signed By Partner',
            'Signed By Partner Date',
            'Signed By UNICEF',
            'Signed By UNICEF Date',
            'Partner Authorized Officer',
            'Amendments',
            'Country Programme',
            'Created',
            'Modified',
        ])

        exported_agreement = dataset[0]
        self.assertEqual(exported_agreement, (
            '{}'.format(self.agreement.pk),
            self.agreement.agreement_number,
            'http://testserver{}'.format(self.agreement.attached_agreement.url),
            unicode(self.agreement.status),
            unicode(self.agreement.partner.name),
            self.agreement.agreement_type,
            '{}'.format(self.agreement.start),
            '{}'.format(self.agreement.end),
            u'',
            '{}'.format(self.agreement.signed_by_partner_date),
            u'',
            '{}'.format(self.agreement.signed_by_unicef_date),
            ', '.join([sm.get_full_name() for sm in self.agreement.authorized_officers.all()]),
            u'',
            '{}'.format(self.agreement.country_programme.name),
            '{}'.format(self.agreement.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
            '{}'.format(self.agreement.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
        ))

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
        super(TestAgreementAmendmentModelExport, self).setUp()
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
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Number',
            'Reference Number',
            'Signed Amendment',
            'Types',
            'Signed Date',
        ])

        exported_agreement = dataset[0]
        self.assertEqual(exported_agreement, (
            self.amendment.number,
            self.agreement.agreement_number,
            'http://testserver{}'.format(self.amendment.signed_amendment.url),
            ', '.join(self.amendment.types),
            '{}'.format(self.amendment.signed_date),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-amendment-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Id',
            'Number',
            'Reference Number',
            'Signed Amendment',
            'Types',
            'Signed Date',
            'Created',
            'Modified',
        ])

        exported_agreement = dataset[0]
        self.assertEqual(exported_agreement, (
            '{}'.format(self.amendment.pk),
            self.amendment.number,
            self.agreement.agreement_number,
            'http://testserver{}'.format(self.amendment.signed_amendment.url),
            ', '.join(self.amendment.types),
            '{}'.format(self.amendment.signed_date),
            '{}'.format(self.amendment.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
            '{}'.format(self.amendment.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
        ))
