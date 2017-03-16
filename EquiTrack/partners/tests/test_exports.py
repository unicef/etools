from __future__ import unicode_literals
from unittest import skip

import xlrd
import datetime
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase

from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import UserFactory, PartnerFactory, AgreementFactory, PartnershipFactory, \
    GovernmentInterventionFactory, InterventionFactory, CountryProgrammeFactory, ResultFactory
from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import GovernmentInterventionResult, ResultType


class TestModelExport(APITenantTestCase):
    def setUp(self):
        super(TestModelExport, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type='Government')
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
            country_programme=CountryProgrammeFactory(wbs="random WBS")
        )

        # This is here to test partner scoping
        AgreementFactory(signed_by_unicef_date=datetime.date.today())

        self.intervention = InterventionFactory(agreement=self.agreement)
        self.government_intervention = GovernmentInterventionFactory(
            partner=self.partner,
            country_programme=self.agreement.country_programme
        )

        output_res_type, _ = ResultType.objects.get_or_create(name='Output')
        self.result = ResultFactory(result_type=output_res_type)
        self.govint_result = GovernmentInterventionResult.objects.create(
            intervention=self.government_intervention,
            result=self.result,
            year=datetime.date.today().year,
            planned_amount=100,
        )

    @skip("wrong endpoint")
    def test_partner_export_api(self):
        response = self.forced_auth_req('get',
                                        '/api/partners/export/',
                                        user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        dataset = Dataset().load(response.content, 'csv')

        self.assertEqual(dataset.height, 2)
        self.assertEqual(dataset._get_headers(),
                         ['vendor_number',
                          'vision_synced',
                          'deleted_flag',
                          'name',
                          'short_name',
                          'alternate_id',
                          'alternate_name',
                          'partner_type',
                          'cso_type',
                          'shared_partner',
                          'address',
                          'email',
                          'phone_number',
                          'risk_rating',
                          'type_of_assessment',
                          'last_assessment_date',
                          'total_ct_cp',
                          'total_ct_cy',
                          'agreement_count',
                          'intervention_count',
                          'active_staff_members'])
        self.assertEqual(dataset[0],
                         ('',
                          '0',
                          '0',
                          self.partner.name,
                          '',
                          '',
                          '',
                          '',
                          '',
                          'No',
                          '',
                          '',
                          '',
                          '',
                          '',
                          '',
                          '',
                          '',
                          '1',
                          '1',
                          'Mace Windu'))

    @skip("wrong api endpoint")
    def test_agreement_export_api(self):
        response = self.forced_auth_req('get',
                                        '/api/partners/{}/agreements/export/'.format(self.partner.id),
                                        user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        dataset = Dataset().load(response.content, 'csv')

        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(),
                         ['reference_number',
                          'partner__vendor_number',
                          'partner__name',
                          'partner__short_name',
                          'start_date',
                          'end_date',
                          'signed_by_partner',
                          'signed_by_partner_date',
                          'signed_by_unicef',
                          'signed_by_unicef_date',
                          'authorized_officers'])
        self.assertEqual(dataset[0],
                         (self.agreement.reference_number,
                          '',
                          self.partner.name,
                          '',
                          '',
                          '',
                          '',
                          '',
                          '',
                          self.agreement.signed_by_unicef_date.strftime('%Y-%m-%d'),
                          ''))

    @skip("Fix export")
    def test_intervention_export_api(self):
        response = self.forced_auth_req('get',
                                        '/api/partners/{}/interventions/export/'.format(self.partner.id),
                                        user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        dataset = Dataset().load(response.content, 'csv')

        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(),
                         ['title',
                          'reference_number',
                          'status',
                          'partner__name',
                          'partnership_type',
                          'sectors',
                          'start_date',
                          'end_date',
                          'result_structure__name',
                          'locations',
                          'initiation_date',
                          'submission_date',
                          'review_date',
                          'days_from_submission_to_signed',
                          'days_from_review_to_signed',
                          'signed_by_partner_date',
                          'partner_manager_name',
                          'signed_by_unicef_date',
                          'unicef_manager_name',
                          'total_unicef_cash',
                          'supplies',
                          'total_budget',
                          'planned_visits'])
        self.assertEqual(dataset[0],
                         ('To save the galaxy from the Empire',
                          self.intervention.reference_number,
                          'in_process',
                          self.partner.name,
                          'PD',
                          '',
                          '',
                          '',
                          '',
                          '',
                          self.intervention.initiation_date.strftime('%Y-%m-%d'),
                          '',
                          '',
                          'Not Submitted',
                          'Not Reviewed',
                          '',
                          '',
                          '',
                          '',
                          '0',
                          '',
                          '0',
                          '0'))

    @skip("Outdated")
    def test_government_export_api(self):
        response = self.forced_auth_req('get',
                                        '/api/partners/{}/government_interventions/export/'.format(self.partner.id),
                                        user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK, response.content)

        dataset = Dataset().load(response.content, 'csv')

        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(),
                         ['number',
                          'partner__name',
                          'result_structure__name',
                          'sectors',
                          'cash_transfer',
                          'year'])
        self.assertEqual(dataset[0],
                         ('RefNumber',
                          self.partner.name,
                          self.government_intervention.result_structure.name,
                          '',
                          '0',
                          datetime.datetime.now().strftime('%Y')))

    def test_government_intervention_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/government_interventions/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(),
                        [
                            'Government Partner',
                            'Country Programme',
                            'Reference Number',
                            'CP Output',
                            'URL',
                        ])

        cp_outputs = ', '.join([
            'Output: {} ({}/{}/{})'.format(
                gr.result.name,
                gr.year,
                gr.planned_amount,
                gr.planned_visits)
            for gr in self.government_intervention.results.all()
        ])
        self.assertEqual(dataset[0],
                        (
                            self.partner.name,
                            self.government_intervention.country_programme.name,
                            self.government_intervention.number,
                            cp_outputs,
                            dataset[0][4],
                        ))

    def test_intervention_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Status',
            'Partner',
            'Partner Type',
            'Agreement',
            'Country Programme',
            'Document Type',
            'Reference Number',
            'Document Title',
            'Start Date',
            'End Date',
            'UNICEF Office',
            'Sectors',
            'Locations',
            'UNICEF Focal Points',
            'CSO Authorized Officials',
            'Population Focus',
            'Humanitarian Response Plan',
            'CP Outputs',
            'RAM Indicators',
            'FR Number(s)',
            'Total UNICEF Budget (Local)',
            'Total UNICEF Budget (USD)',
            'Total CSO Budget (USD)',
            'Total CSO Budget (Local)',
            'Planned Programmatic Visits',
            'Planned Spot Checks',
            'Planned Audits',
            'Document Submission Date by CSO',
            'Submission Date to PRC',
            'Review Date by PRC',
            'Signed by Partner',
            'Signed by Partner Date',
            'Signed by UNICEF',
            'Signed by UNICEF Date',
            'Supply Plan',
            'Distribution Plan',
            'URL'
        ])

    def test_agreement_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
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

    def test_partners_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
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
