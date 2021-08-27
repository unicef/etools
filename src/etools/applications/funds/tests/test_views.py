import json
from datetime import datetime, timedelta
from pathlib import Path

from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import (
    DonorFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    GrantFactory,
)
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.tests.vcrpy import VCR


class TestFRHeaderView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        partner = PartnerFactory(vendor_number="PVN")
        agreement = AgreementFactory(partner=partner)
        cls.intervention = InterventionFactory(agreement=agreement)

    def setUp(self):
        vendor_code = self.intervention.agreement.partner.vendor_number
        self.fr_1 = FundsReservationHeaderFactory(intervention=None, currency="USD", vendor_code=vendor_code)
        self.fr_2 = FundsReservationHeaderFactory(intervention=None, currency="USD", vendor_code=vendor_code)
        self.fr_3 = FundsReservationHeaderFactory(intervention=None, currency="RON")

    def run_request(self, data):
        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.unicef_staff,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_get_one_fr(self):

        data = {'values': self.fr_1.fr_number}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 1)
        self.assertEqual(result['total_actual_amt'], float(self.fr_1.actual_amt_local))
        self.assertEqual(result['total_outstanding_amt'], float(self.fr_1.outstanding_amt_local))
        self.assertEqual(result['total_frs_amt'], float(self.fr_1.total_amt_local))
        self.assertEqual(result['total_intervention_amt'], float(self.fr_1.intervention_amt))

    def test_get_two_frs(self):

        data = {'values': ','.join([self.fr_1.fr_number, self.fr_2.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

        # Make sure result numbers match up
        # float the Decimal sum
        self.assertEqual(result['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt_local, self.fr_2.actual_amt_local])))
        self.assertEqual(result['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt_local, self.fr_2.outstanding_amt_local])))
        self.assertEqual(result['total_frs_amt'],
                         float(sum([self.fr_1.total_amt_local, self.fr_2.total_amt_local])))
        self.assertEqual(result['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))

    def test_get_earliest_start_date_from_two_frs(self):

        data = {'values': ','.join([self.fr_1.fr_number, self.fr_2.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

        self.assertEqual(datetime.strptime(result['earliest_start_date'], '%Y-%m-%d').date(),
                         min([self.fr_1.start_date, self.fr_2.start_date]))
        self.assertEqual(datetime.strptime(result['latest_end_date'], '%Y-%m-%d').date(),
                         max([self.fr_1.end_date, self.fr_2.end_date]))

    def test_get_earliest_start_date_from_one_fr(self):

        data = {'values': ','.join([self.fr_1.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 1)

        self.assertEqual(datetime.strptime(result['earliest_start_date'], '%Y-%m-%d').date(),
                         self.fr_1.start_date)
        self.assertEqual(datetime.strptime(result['latest_end_date'], '%Y-%m-%d').date(),
                         self.fr_1.end_date)

    def test_get_fail_with_no_values(self):
        data = {}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], 'Values are required')

    @VCR.use_cassette(str(Path(__file__).parent / 'vcr_cassettes/fund_reservation_invalid.yml'))
    def test_get_fail_with_non_existant_values(self):
        data = {'values': ','.join(['another bad value', 'im a bad value', ])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], 'One or more of the FRs are used by another PD/SPD or '
                                          'could not be found in eTools.')
    # TODO: add tests to cover, frs correctly brought in from unittest.mock. with correct vendor numbers, FR missing from vision,
    # FR with multiple line items, and FR with only one line item.

    @VCR.use_cassette(str(Path(__file__).parent / 'vcr_cassettes/fund_reservation.yml'))
    def test_get_fail_with_already_used_fr(self):
        new_intervention = InterventionFactory()
        self.fr_1.intervention = self.intervention
        self.fr_1.save()
        data = {'values': ','.join(['9999', self.fr_1.fr_number]),
                'intervention': new_intervention.pk}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], f'FR #{self.fr_1} is already being used by PD/SPD ref [{self.intervention}]')

    @VCR.use_cassette(str(Path(__file__).parent / 'vcr_cassettes/fund_reservation.yml'))
    def test_get_success_sync_vision(self):
        """set vendor_code to PVN in the cassette"""
        self.fr_1.intervention = self.intervention
        self.fr_1.save()
        data = {'values': ','.join(['9999', self.fr_1.fr_number]),
                'intervention': self.intervention.id}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

    def test_get_fail_with_intervention_id(self):
        other_intervention = InterventionFactory()
        fth_value = 'im a bad value'
        FundsReservationHeaderFactory(fr_number=fth_value, intervention=other_intervention, currency="USD")
        data = {'values': ','.join([fth_value, self.fr_1.fr_number]), 'intervention': self.intervention.pk}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'],
                         'FR #{} is already being used by PD/SPD ref [{}]'.format(fth_value, other_intervention))

    def test_get_success_with_expired_fr(self):
        self.fr_1.end_date = timezone.now().date() - timedelta(days=1)
        self.fr_1.save()
        data = {'values': ','.join([self.fr_2.fr_number, self.fr_1.fr_number])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)

    def test_get_fail_with_intervention_fr(self):
        self.fr_1.intervention = self.intervention
        self.fr_1.save()
        data = {'values': ','.join([self.fr_2.fr_number, self.fr_1.fr_number])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'],
                         'One or more of the FRs are used by another PD/SPD '
                         'or could not be found in eTools.')

    def test_get_with_intervention_fr(self):
        self.fr_1.intervention = self.intervention
        self.fr_1.save()
        data = {'values': ','.join([self.fr_2.fr_number, self.fr_1.fr_number]),
                'intervention': self.intervention.id}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)
        self.assertEqual(result['total_actual_amt'], float(sum([self.fr_1.actual_amt_local,
                                                                self.fr_2.actual_amt_local])))
        self.assertEqual(result['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt_local, self.fr_2.outstanding_amt_local])))
        self.assertEqual(result['total_frs_amt'],
                         float(sum([self.fr_1.total_amt_local, self.fr_2.total_amt_local])))
        self.assertEqual(result['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))

    def test_grants_filter(self):
        """Check that filtering on grant returns expected result"""
        grant_number = "G123"
        grant = GrantFactory(name=grant_number)
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number
        )
        data = {
            "values": self.fr_1.fr_number,
            "grants": grant.pk,
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 1)

    def test_grants_many_filter(self):
        """Check that filtering on multiple grants returns expected result"""
        grant_number_1 = "G123"
        grant_number_2 = "G124"
        grant_1 = GrantFactory(name=grant_number_1)
        grant_2 = GrantFactory(name=grant_number_2)
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number_1
        )
        FundsReservationItemFactory(
            fund_reservation=self.fr_2,
            grant_number=grant_number_2
        )
        FundsReservationHeaderFactory()
        data = {
            "values": ",".join([self.fr_1.fr_number, self.fr_2.fr_number]),
            "grants": ",".join([str(grant_1.pk), str(grant_2.pk)]),
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

    def test_donors_filter(self):
        """Check that filtering on donor returns expected result"""
        donor = DonorFactory()
        grant_number = "G123"
        GrantFactory(
            donor=donor,
            name=grant_number,
        )
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number
        )
        data = {
            "values": self.fr_1.fr_number,
            "donors": donor.pk,
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 1)

    def test_donors_many_filter(self):
        """Check that filtering on multiple donors returns expected result"""
        donor_1 = DonorFactory()
        donor_2 = DonorFactory()
        grant_number_1 = "G123"
        grant_number_2 = "G124"
        GrantFactory(
            donor=donor_1,
            name=grant_number_1,
        )
        GrantFactory(
            donor=donor_2,
            name=grant_number_2,
        )
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number_1
        )
        FundsReservationItemFactory(
            fund_reservation=self.fr_2,
            grant_number=grant_number_2
        )
        FundsReservationHeaderFactory()
        data = {
            "values": ",".join([self.fr_1.fr_number, self.fr_2.fr_number]),
            "donors": ",".join([str(donor_1.pk), str(donor_2.pk)]),
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

    def test_frs_vendor_code_mismatch(self):
        data = {'values': ','.join([self.fr_1.fr_number, self.fr_3.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('FRs selected relate to various partners', result['error'])

    def test_frs_partner_vendor_code_mismatch(self):
        data = {'values': ','.join([self.fr_3.fr_number]),
                'intervention': self.intervention.pk}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vendor number of the selected implementing partner in eTools does not '
                      'match the vendor number entered in the FR in VISION', result['error'])

    def test_frs_partner_vendor_code_ok(self):
        data = {'values': ','.join([self.fr_1.fr_number]),
                'intervention': self.intervention.pk}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)

    def test_frs_currencies_match_ok(self):
        data = {'values': ','.join([self.fr_1.fr_number, self.fr_2.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(result['currencies_match'], True)
        self.assertNotEqual(result['total_intervention_amt'], 0)

    def test_frs_currencies_mismatch_ok(self):
        self.fr_2.currency = 'LBP'
        self.fr_2.save()
        data = {'values': ','.join([self.fr_1.fr_number, self.fr_2.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(result['currencies_match'], False)
        self.assertEqual(result['total_intervention_amt'], 0)
