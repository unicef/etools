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
            country_programme=CountryProgrammeFactory(wbs="random WBS"))
        # This is here to test partner scoping
        AgreementFactory(signed_by_unicef_date=datetime.date.today())
        self.intervention = InterventionFactory(agreement=self.agreement)
        self.government_intervention = GovernmentInterventionFactory(partner=self.partner)

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
            'Output: {} ({},{},{})'.format(
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
