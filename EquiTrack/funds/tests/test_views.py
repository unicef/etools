from __future__ import unicode_literals

from datetime import timedelta, datetime
import json

from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from EquiTrack.factories import (
    DonorFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    GrantFactory,
    InterventionFactory,
    UserFactory,
)


class TestFRHeaderView(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory()

    def setUp(self):
        super(TestFRHeaderView, self).setUp()
        self.fr_1 = FundsReservationHeaderFactory(intervention=None)
        self.fr_2 = FundsReservationHeaderFactory(intervention=None)

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
        self.assertEqual(result['total_actual_amt'], float(self.fr_1.actual_amt))
        self.assertEqual(result['total_outstanding_amt'], float(self.fr_1.outstanding_amt))
        self.assertEqual(result['total_frs_amt'], float(self.fr_1.total_amt))
        self.assertEqual(result['total_intervention_amt'], float(self.fr_1.intervention_amt))

    def test_get_two_frs(self):

        data = {'values': ','.join([self.fr_1.fr_number, self.fr_2.fr_number])}

        status_code, result = self.run_request(data)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)

        # Make sure result numbers match up
        # float the Decimal sum
        self.assertEqual(result['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEqual(result['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEqual(result['total_frs_amt'],
                         float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
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

    def test_get_fail_with_nonexistant_values(self):
        data = {'values': ','.join(['im a bad value', 'another bad value'])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'],
                         'One or more of the FRs are used by another PD/SSFA '
                         'or could not be found in eTools.')

    def test_get_fail_with_one_bad_value(self):
        data = {'values': ','.join(['im a bad value', self.fr_1.fr_number])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'],
                         'One or more of the FRs are used by another PD/SSFA '
                         'or could not be found in eTools.')

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
                         'One or more of the FRs are used by another PD/SSFA '
                         'or could not be found in eTools.')

    def test_get_with_intervention_fr(self):
        self.fr_1.intervention = self.intervention
        self.fr_1.save()
        data = {'values': ','.join([self.fr_2.fr_number, self.fr_1.fr_number]),
                'intervention': self.intervention.id}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)
        self.assertEqual(result['total_actual_amt'], float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEqual(result['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEqual(result['total_frs_amt'],
                         float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
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

    def test_grants_filter_invalid(self):
        """Check that filtering on invalid grant returns empty result"""
        grant_number = "G123"
        GrantFactory(name=grant_number)
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number
        )
        data = {
            "values": self.fr_1.fr_number,
            "grants": "404",
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 0)

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

    def test_donors_filter_invalid(self):
        """Check that filtering on invalid donors returns empty result"""
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
            "donors": "404",
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 0)

    def test_grant_donors_mismatch(self):
        """Check that filtering on donors and grant not related to donor,
        returns empty result
        """
        donor = DonorFactory()
        GrantFactory(
            donor=donor,
        )
        grant_number = "G123"
        grant = GrantFactory(
            name=grant_number,
        )
        FundsReservationItemFactory(
            fund_reservation=self.fr_1,
            grant_number=grant_number
        )
        data = {
            "values": self.fr_1.fr_number,
            "grants": grant.pk,
            "donors": donor.pk,
        }
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 0)
