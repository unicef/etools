from __future__ import unicode_literals

import datetime
import tempfile

from django.core.urlresolvers import reverse
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import (
    AssessmentFactory,
    PartnerFactory,
    PartnerStaffFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase


class PartnerModelExportTestCase(APITenantTestCase):
    def setUp(self):
        super(PartnerModelExportTestCase, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
            partner_type='Government',
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
        self.partnerstaff = PartnerStaffFactory(partner=self.partner)


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
        dataset = Dataset().load(response.content, 'csv')
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
            'URL'
        ])
        deleted_flag = "Yes" if self.partner.deleted_flag else "No"
        blocked = "Yes" if self.partner.blocked else "No"

        test_option = filter(lambda e: e[0] == self.partner.vendor_number, dataset)[0]
        self.assertEqual(test_option, (
            self.partner.vendor_number,
            unicode(self.partner.name),
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
            ', '.join(["{} ({})".format(sm.get_full_name(), sm.email)
                       for sm in self.partner.staff_members.filter(active=True).all()]),
            u'https://testserver/pmp/partners/{}/details/'.format(self.partner.id)
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Id',
            'Vendor Number',
            'Organizations Full Name',
            'Short Name',
            'Alternate Name',
            'Alternate Id',
            'Description',
            'Partner Type',
            'Shared Partner',
            'Shared Partner (old)',
            'HACT',
            'Address',
            'Street Address',
            'City',
            'Postal Code',
            'Country',
            'Phone Number',
            'Email Address',
            'Risk Rating',
            'Date Last Assessed Against Core Values',
            'Actual Cash Transfer for CP (USD)',
            'Actual Cash Transfer for Current Year (USD)',
            'Marked for Deletion',
            'Blocked',
            'VISION Synced',
            'Hidden',
            'Assessment Type',
            'Date Assessed',
            'Assessment Type (Date Assessed)',
            'Staff Members',
        ])
        deleted_flag = "Yes" if self.partner.deleted_flag else "No"
        blocked = "Yes" if self.partner.blocked else "No"
        vision_synced = "Yes" if self.partner.vision_synced else "No"
        hidden = "Yes" if self.partner.hidden else "No"

        exported_partner_organization = dataset[0]
        self.assertEqual(exported_partner_organization, (
            '{}'.format(self.partner.pk),
            self.partner.vendor_number,
            unicode(self.partner.name),
            self.partner.short_name,
            self.partner.alternate_name,
            u'',
            u'',
            "{}".format(self.partner.partner_type),
            u', '.join([x for x in self.partner.shared_with]),
            self.partner.shared_partner,
            "\n".join(
                ["{}: {}".format(x, self.partner.hact_values[x])
                 for x in sorted(list(self.partner.hact_values))]
            ),
            self.partner.address,
            u'',
            u'',
            u'',
            u'',
            self.partner.phone_number,
            self.partner.email,
            self.partner.rating,
            u'{}'.format(self.partner.core_values_assessment_date),
            u'{:.2f}'.format(self.partner.total_ct_cp),
            u'{:.2f}'.format(self.partner.total_ct_cy),
            deleted_flag,
            blocked,
            vision_synced,
            hidden,
            self.partner.type_of_assessment,
            u'{}'.format(self.partner.last_assessment_date),
            u'',
            ', '.join(["{} ({})".format(sm.get_full_name(), sm.email)
                       for sm in self.partner.staff_members.filter(active=True).all()]),
        ))


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
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(dataset._get_headers(), [
            "Partner",
            "Title",
            "First Name",
            "Last Name",
            "Email Address",
            "Phone Number",
            "Active",
        ])
        active = "Yes" if self.partnerstaff.active else "No"

        self.assertIn(
            (
                "{}".format(self.partner.pk),
                self.partnerstaff.title,
                self.partnerstaff.first_name,
                self.partnerstaff.last_name,
                self.partnerstaff.email,
                u"",
                active,
            ),
            dataset
        )

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-staff-members-list', args=[self.partner.pk]),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Partner Name",
            "Title",
            "First Name",
            "Last Name",
            "Email Address",
            "Phone Number",
            "Active",
        ])
        active = "Yes" if self.partnerstaff.active else "No"

        self.assertIn(
            (
                "{}".format(self.partnerstaff.pk),
                self.partner.name,
                self.partnerstaff.title,
                self.partnerstaff.first_name,
                self.partnerstaff.last_name,
                self.partnerstaff.email,
                u"",
                active,
            ),
            dataset
        )


class TestPartnerOrganizationAssessmentModelExport(PartnerModelExportTestCase):
    def setUp(self):
        super(TestPartnerOrganizationAssessmentModelExport, self).setUp()
        report = tempfile.NamedTemporaryFile(suffix=".pdf").name
        self.assessment = AssessmentFactory(
            partner=self.partner,
            report=report
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
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Partner Name",
            "Type",
            "Other Agencies",
            "Expected Budget",
            "Notes",
            "Date Requested",
            "Requesting Officer",
            "Approving Officer",
            "Date Planned",
            "Date Completed",
            "Rating",
            "Report File",
            "Current",
        ])
        current = "Yes" if self.assessment.current else "No"

        assessment = dataset[0]
        self.assertEqual(assessment, (
            self.assessment.partner.name,
            self.assessment.type,
            self.assessment.names_of_other_agencies,
            u"{}".format(self.assessment.expected_budget),
            self.assessment.notes,
            u"{}".format(self.assessment.requested_date),
            self.assessment.requesting_officer.email,
            self.assessment.approving_officer.email,
            u"{}".format(self.assessment.planned_date),
            u"{}".format(self.assessment.completed_date),
            self.assessment.rating,
            'http://testserver{}'.format(self.assessment.report.url),
            current,
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-assessment'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Partner Name",
            "Type",
            "Other Agencies",
            "Expected Budget",
            "Notes",
            "Date Requested",
            "Requesting Officer",
            "Approving Officer",
            "Date Planned",
            "Date Completed",
            "Rating",
            "Report File",
            "Current",
        ])
        current = "Yes" if self.assessment.current else "No"

        assessment = dataset[0]
        self.assertEqual(assessment, (
            u"{}".format(self.assessment.pk),
            self.assessment.partner.name,
            self.assessment.type,
            self.assessment.names_of_other_agencies,
            u"{}".format(self.assessment.expected_budget),
            self.assessment.notes,
            u"{}".format(self.assessment.requested_date),
            self.assessment.requesting_officer.email,
            self.assessment.approving_officer.email,
            u"{}".format(self.assessment.planned_date),
            u"{}".format(self.assessment.completed_date),
            self.assessment.rating,
            'http://testserver{}'.format(self.assessment.report.url),
            current,
        ))
