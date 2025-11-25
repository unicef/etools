import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.funds.tests.factories import (
    DonorFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    GrantFactory,
)
from etools.applications.governments.tests.factories import GDDFactory
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Agreement, Intervention
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    PartnerFactory,
    SignedInterventionFactory,
)
from etools.applications.users.tests.factories import UserFactory
from etools.applications.vision.models import VisionSyncLog
from etools.libraries.tests.vcrpy import VCR


class TestFRHeaderView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        partner = PartnerFactory(organization=OrganizationFactory(vendor_number="PVN"))
        agreement = AgreementFactory(partner=partner)
        cls.intervention = InterventionFactory(agreement=agreement)

        cls.government = PartnerFactory(
            organization=OrganizationFactory(name='Partner 1', vendor_number="P1", organization_type=OrganizationType.GOVERNMENT))
        cls.gdd = GDDFactory(partner=cls.government)

    def setUp(self):
        vendor_code = self.intervention.agreement.partner.vendor_number
        self.fr_1 = FundsReservationHeaderFactory(intervention=None, currency="USD", vendor_code=vendor_code)
        self.fr_2 = FundsReservationHeaderFactory(intervention=None, currency="USD", vendor_code=vendor_code)
        self.fr_3 = FundsReservationHeaderFactory(intervention=None, currency="RON")
        self.fr_4 = FundsReservationHeaderFactory(intervention=None, currency="AFG", vendor_code=self.government.vendor_number)
        self.fr_5 = FundsReservationHeaderFactory(intervention=None, currency="AFG", vendor_code=self.government.vendor_number)

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
    def test_get_fail_with_non_existent_values(self):
        data = {'values': ','.join(['another bad value', 'im a bad value', ])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], 'The Fund Reservation another bad value could not be found in eTools or in VISION. '
                                          'Please make sure it has been created in the VISION platform first.')
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
        self.assertEqual(result['error'], f'FR #{self.fr_1} is already being used by Document ref [{self.intervention}]')

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

    @VCR.use_cassette(str(Path(__file__).parent / 'vcr_cassettes/fund_reservation_not_found.yml'))
    def test_get_fail_sync_vision_not_found(self):
        data = {'values': ','.join(['9999', self.fr_4.fr_number]),
                'gpd': self.gdd.id}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The Fund Reservation {} could not be found in eTools or in VISION. '
                      'Please make sure it has been created in the VISION platform first.'.format(9999), result['error'])

    def test_get_fail_with_intervention_id(self):
        other_intervention = InterventionFactory()
        fth_value = 'im a bad value'
        FundsReservationHeaderFactory(fr_number=fth_value, intervention=other_intervention, currency="USD")
        data = {'values': ','.join([fth_value, self.fr_1.fr_number]), 'intervention': self.intervention.pk}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'],
                         'FR #{} is already being used by Document ref [{}]'.format(fth_value, other_intervention))

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
        self.assertEqual(result['error'], 'One or more of the FRs requested are used by another Document.')

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

    def test_get_fail_with_gpd_fr(self):
        self.fr_4.gdd = self.gdd
        self.fr_4.save(update_fields=['gdd'])
        data = {'values': ','.join([self.fr_2.fr_number, self.fr_4.fr_number])}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], 'One or more of the FRs requested are used by another Document.')

    def test_get_with_gdd_fr(self):
        data = {'values': ','.join([self.fr_4.fr_number, self.fr_5.fr_number]),
                'gdd': self.gdd.id}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(result['frs']), 2)
        self.assertEqual(result['total_actual_amt'], float(sum([self.fr_4.actual_amt_local,
                                                                self.fr_5.actual_amt_local])))
        self.assertEqual(result['total_outstanding_amt'],
                         float(sum([self.fr_4.outstanding_amt_local, self.fr_5.outstanding_amt_local])))
        self.assertEqual(result['total_frs_amt'],
                         float(sum([self.fr_4.total_amt_local, self.fr_5.total_amt_local])))
        self.assertEqual(result['total_intervention_amt'],
                         float(sum([self.fr_4.intervention_amt, self.fr_5.intervention_amt])))

    def test_get_with_gpd_not_found(self):
        data = {'values': ','.join([self.fr_4.fr_number, self.fr_5.fr_number]),
                'gdd': 12345}
        status_code, result = self.run_request(data)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result['error'], 'GPD with id 12345 could not be found.')


class TestPDExternalReservationAPIView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(email='test@example.com', realms__data=[])
        cls.token = Token(user=cls.user, key='testkey')
        cls.token.save()
        cls.client = APIClient()

        cls.partner = PartnerFactory(organization=OrganizationFactory())
        cls.agreement = AgreementFactory(
            partner=cls.partner,
            status=Agreement.SIGNED,
            signed_by_unicef_date=date.today() - timedelta(days=2),
            signed_by_partner_date=date.today() - timedelta(days=2),
            start=date.today() - timedelta(days=2),
        )
        cls.intervention = InterventionFactory(agreement=cls.agreement)

        try:
            cls.admin_user = get_user_model().objects.get(username=settings.TASK_ADMIN_USER)
        except get_user_model().DoesNotExist:
            cls.admin_user = UserFactory(username=settings.TASK_ADMIN_USER)

        cls.data = {
            "fr_items": [
                {
                    "fr_ref_number": "ref1",
                    "line_item": 111,
                    "wbs": "3750/A0/04/110/002/001",
                    "donor": "UNDP USA",
                    "donor_code": "U99905",
                    "grant_number": "SC080517",
                    "fund": "SC",
                    "overall_amount": "84437.72",
                    "overall_amount_dc": "84437.72",
                    "due_date": "2012-02-23",
                    "line_item_text": "LEGAL AID TO CHILDREN IN CONFLICT WITH LAW"
                },
                {
                    "fr_ref_number": "ref2",
                    "line_item": 222,
                    "wbs": "3750/A0/04/110/002/001",
                    "donor": "N/A",
                    "donor_code": "N/A",
                    "grant_number": "NON-GRANT",
                    "fund": "GC",
                    "overall_amount": "25417.00",
                    "overall_amount_dc": "25417.00",
                    "due_date": "2012-12-17",
                    "line_item_text": "LEGAL AID TO CHILDREN IN CONFLICT WITH LAW"
                }
            ],
            "business_area_code": cls.tenant.business_area_code,
            "pd_reference_number": cls.intervention.number,
            "vendor_code": cls.partner.vendor_number,
            "fr_number": "040000056770",
            "document_date": "2024-07-08",
            "fr_type": "Programme Document Against PCA",
            "currency": "USD",
            "document_text": "PCA FOR CHILD RIGHTS PROJECT OF AJPRODHO",
            "intervention_amt": "110487.20",
            "total_amt": "108597.42",
            "total_amt_local": "109854.72",
            "actual_amt": "110487.20",
            "actual_amt_local": "0.00",
            "outstanding_amt": "12.98",
            "outstanding_amt_local": "0.00",
            "start_date": "2012-01-26",
            "end_date": "2024-07-08",
            "multi_curr_flag": True,
            "completed_flag": False,
            "delegated": False
        }

    @staticmethod
    def get_instance_str(value):
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _assert_payload(self, funds_reservation, data):
        for field in ['vendor_code', 'fr_number', 'document_date', 'fr_type', 'currency', 'document_text',
                      'intervention_amt', 'total_amt', 'total_amt_local', 'actual_amt', 'actual_amt_local',
                      'outstanding_amt', 'outstanding_amt_local', 'start_date', 'end_date', 'multi_curr_flag',
                      'completed_flag', 'delegated']:
            actual_value = getattr(funds_reservation, field)
            self.assertEqual(self.get_instance_str(actual_value), data[field])

        self.assertEqual(funds_reservation.fr_items.count(), len(data['fr_items']))
        for actual_item, expected_item in zip(funds_reservation.fr_items.all(), data['fr_items']):
            for field in data['fr_items'][0].keys():
                actual_value = getattr(actual_item, field)
                self.assertEqual(self.get_instance_str(actual_value), expected_item[field])

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_201_auto_transition_conditions_not_met(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        self.assertEqual(self.intervention.status, Intervention.DRAFT)

        self.data["pd_reference_number"] = self.intervention.number

        response = self.client.post(reverse('funds:external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(self.intervention.frs.count(), 1)
        funds_reservation = self.intervention.frs.first()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        self._assert_payload(funds_reservation, self.data)

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_201_auto_transition_conditions_met(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        unicef_staff = UserFactory(is_staff=True)
        partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.partner.organization
        )
        signed_intervention = SignedInterventionFactory(
            agreement=self.agreement,
            budget_owner=unicef_staff,
            unicef_signatory=unicef_staff,
            partner_authorized_officer_signatory=self.partner.active_staff_members.all().first(),
            partner_focal_points=[partner_user],
            unicef_focal_points=[unicef_staff]
        )

        self.assertEqual(signed_intervention.status, Intervention.SIGNED)

        self.data["pd_reference_number"] = signed_intervention.number

        response = self.client.post(reverse('funds:external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(signed_intervention.frs.count(), 1)

        signed_intervention.refresh_from_db()
        self.assertEqual(signed_intervention.status, Intervention.ACTIVE)

        funds_reservation = signed_intervention.frs.first()

        self._assert_payload(funds_reservation, self.data)

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_404_pd_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        self.data["pd_reference_number"] = 'inexistent ref number'

        response = self.client.post(reverse('funds:external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
        vision_log = VisionSyncLog.objects.filter(
            handler_name='EZHactFundsReservation'
        ).last()
        self.assertEqual(vision_log.data, self.data)

    def test_post_unauthorized_401(self):
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        with override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='wrongkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')

            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        with override_settings(ETOOLS_EZHACT_EMAIL='wrong@example.com', ETOOLS_EZHACT_TOKEN='testkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')
            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        tenant_switch.is_active = False
        tenant_switch.save()
        with override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')
            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)


class TestGPDExternalReservationAPIView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(email='test@example.com', realms__data=[])
        cls.token = Token(user=cls.user, key='testkey')
        cls.token.save()
        cls.client = APIClient()

        cls.partner = PartnerFactory(organization=OrganizationFactory())
        cls.agreement = AgreementFactory(
            partner=cls.partner,
            status=Agreement.SIGNED,
            signed_by_unicef_date=date.today() - timedelta(days=2),
            signed_by_partner_date=date.today() - timedelta(days=2),
            start=date.today() - timedelta(days=2),
        )
        cls.gdd = GDDFactory(agreement=cls.agreement)

        try:
            cls.admin_user = get_user_model().objects.get(username=settings.TASK_ADMIN_USER)
        except get_user_model().DoesNotExist:
            cls.admin_user = UserFactory(username=settings.TASK_ADMIN_USER)

        cls.data = {
            "fr_items": [
                {
                    "fr_ref_number": "ref1",
                    "line_item": 111,
                    "wbs": "3750/A0/04/110/002/001",
                    "donor": "UNDP USA",
                    "donor_code": "U99905",
                    "grant_number": "SC080517",
                    "fund": "SC",
                    "overall_amount": "84437.72",
                    "overall_amount_dc": "84437.72",
                    "due_date": "2012-02-23",
                    "line_item_text": "LEGAL AID TO CHILDREN IN CONFLICT WITH LAW"
                },
                {
                    "fr_ref_number": "ref2",
                    "line_item": 222,
                    "wbs": "3750/A0/04/110/002/001",
                    "donor": "N/A",
                    "donor_code": "N/A",
                    "grant_number": "NON-GRANT",
                    "fund": "GC",
                    "overall_amount": "25417.00",
                    "overall_amount_dc": "25417.00",
                    "due_date": "2012-12-17",
                    "line_item_text": "LEGAL AID TO CHILDREN IN CONFLICT WITH LAW"
                }
            ],
            "business_area_code": cls.tenant.business_area_code,
            "gpd_reference_number": cls.gdd.number,
            "vendor_code": cls.partner.vendor_number,
            "fr_number": "040000056770",
            "document_date": "2024-07-08",
            # TODO tbd on fr_type and document_text
            "fr_type": "Programme Document Against PCA",
            "currency": "USD",
            "document_text": "PCA FOR CHILD RIGHTS PROJECT OF AJPRODHO",
            "intervention_amt": "110487.20",
            "total_amt": "108597.42",
            "total_amt_local": "109854.72",
            "actual_amt": "110487.20",
            "actual_amt_local": "0.00",
            "outstanding_amt": "12.98",
            "outstanding_amt_local": "0.00",
            "start_date": "2012-01-26",
            "end_date": "2024-07-08",
            "multi_curr_flag": True,
            "completed_flag": False,
            "delegated": False
        }

    @staticmethod
    def get_instance_str(value):
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _assert_payload(self, funds_reservation, data):
        for field in ['vendor_code', 'fr_number', 'document_date', 'fr_type', 'currency', 'document_text',
                      'intervention_amt', 'total_amt', 'total_amt_local', 'actual_amt', 'actual_amt_local',
                      'outstanding_amt', 'outstanding_amt_local', 'start_date', 'end_date', 'multi_curr_flag',
                      'completed_flag', 'delegated']:
            actual_value = getattr(funds_reservation, field)
            self.assertEqual(self.get_instance_str(actual_value), data[field])

        self.assertEqual(funds_reservation.fr_items.count(), len(data['fr_items']))
        for actual_item, expected_item in zip(funds_reservation.fr_items.all(), data['fr_items']):
            for field in data['fr_items'][0].keys():
                actual_value = getattr(actual_item, field)
                self.assertEqual(self.get_instance_str(actual_value), expected_item[field])

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_201_auto_transition_conditions_not_met(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        self.assertEqual(self.intervention.status, Intervention.DRAFT)

        self.data["pd_reference_number"] = self.intervention.number

        response = self.client.post(reverse('funds:pd-external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(self.gdd.frs.count(), 1)
        funds_reservation = self.gdd.frs.first()
        self.gdd.refresh_from_db()
        self.assertEqual(self.gdd.status, Intervention.DRAFT)
        self._assert_payload(funds_reservation, self.data)

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_201_auto_transition_conditions_met(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        unicef_staff = UserFactory(is_staff=True)
        partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.partner.organization
        )
        signed_intervention = SignedInterventionFactory(
            agreement=self.agreement,
            budget_owner=unicef_staff,
            unicef_signatory=unicef_staff,
            partner_authorized_officer_signatory=self.partner.active_staff_members.all().first(),
            partner_focal_points=[partner_user],
            unicef_focal_points=[unicef_staff]
        )

        self.assertEqual(signed_intervention.status, Intervention.SIGNED)

        self.data["gpd_reference_number"] = signed_intervention.number

        response = self.client.post(reverse('funds:pd-external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(signed_intervention.frs.count(), 1)

        signed_intervention.refresh_from_db()
        self.assertEqual(signed_intervention.status, Intervention.ACTIVE)

        funds_reservation = signed_intervention.frs.first()

        self._assert_payload(funds_reservation, self.data)

    @override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey')
    def test_post_404_pd_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        self.data["gpd_reference_number"] = 'inexistent ref number'

        response = self.client.post(reverse('funds:external-funds-reservation'), self.data, format='json')
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
        vision_log = VisionSyncLog.objects.filter(
            handler_name='EZHactGPDFundsReservation'
        ).last()
        self.assertEqual(vision_log.data, self.data)

    def test_post_unauthorized_401(self):
        tenant_switch = TenantSwitchFactory(name="ezhact_external_fr_disabled")
        tenant_switch.countries.add(connection.tenant)
        self.assertTrue(tenant_switch.is_active())

        with override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='wrongkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')

            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        with override_settings(ETOOLS_EZHACT_EMAIL='wrong@example.com', ETOOLS_EZHACT_TOKEN='testkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')
            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        tenant_switch.is_active = False
        tenant_switch.save()
        with override_settings(ETOOLS_EZHACT_EMAIL='test@example.com', ETOOLS_EZHACT_TOKEN='testkey'):
            response = self.client.post(reverse('funds:external-funds-reservation'), data={}, format='json')
            self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)