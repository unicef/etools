from __future__ import unicode_literals

import json
import mock

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import DSARegionFactory, AirlineCompanyFactory
from t2f.models import Travel, ModeOfTravel
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory


class ThresholdTest(APITenantTestCase):
    def setUp(self):
        super(ThresholdTest, self).setUp()
        self.traveler = UserFactory(is_staff=True)
        self.unicef_staff = UserFactory(is_staff=True)
        # self.travel = TravelFactory(traveler=self.traveler,
        #                             supervisor=self.unicef_staff)
        workspace = self.unicef_staff.profile.country
        workspace.threshold_tae_usd = 100
        workspace.threshold_tre_usd = 100
        workspace.save()

    def _prepare_test(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()
        dsaregion = DSARegionFactory()
        airlines = AirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.traveler)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        return travel_id, data

    @override_settings(DISABLE_INVOICING=False)
    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_threshold_with_invoicing(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel': {}}

        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.traveler)

        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        # Threshold reached. Send for approval
        data = response_json
        data['expenses'][0]['amount'] = '300'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.traveler)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

    @override_settings(DISABLE_INVOICING=True)
    def test_threshold_without_invoicing(self):
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        # Threshold reached. Send for payment (skip approval if invoicing is disabled)
        data = response_json
        data['expenses'][0]['amount'] = '300'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SENT_FOR_PAYMENT)

    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_multi_step_reach(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel': {}}

        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.traveler)

        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        # Threshold not reached yet. Still send for payment
        data = response_json
        data['expenses'][0]['amount'] = '180'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.traveler)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SENT_FOR_PAYMENT)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

        # Threshold reached. Send for approval
        currency = CurrencyFactory()
        # If vendor number is empty, considered as estimated travel cost
        # and should be included while calculating the threshold
        expense_type = ExpenseTypeFactory(vendor_number='')

        data = response_json
        data['expenses'].append({'amount': '41',
                                 'type': expense_type.id,
                                 'currency': currency.id,
                                 'document_currency': currency.id})
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.traveler)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

        travel = Travel.objects.get(id=travel_id)
        self.assertEqual(travel.approved_cost_traveler, 0)
        self.assertEqual(travel.approved_cost_travel_agencies, 120)

    @override_settings(DISABLE_INVOICING=True)
    def test_threshold_check_on_complete_without_invoices(self):
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['expenses'][0]['amount'] = '1000'
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.CERTIFIED)

    @override_settings(DISABLE_INVOICING=False)
    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_threshold_check_on_complete(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel': {}}
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['expenses'][0]['amount'] = '1000'
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.CERTIFICATION_SUBMITTED)

    @override_settings(DISABLE_INVOICING=False)
    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_threshold_check_on_complete_not_reached(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel': {}}
        # Threshold not reached
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['expenses'][0]['amount'] = '140'
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.CERTIFIED)
