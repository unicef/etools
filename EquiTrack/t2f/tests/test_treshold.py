from __future__ import unicode_literals

from unittest import skip
import json
from StringIO import StringIO

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from EquiTrack.factories import UserFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import DSARegion
from publics.tests.factories import BusinessAreaFactory
from t2f.models import TravelAttachment, Travel, ModeOfTravel
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, FundFactory, AirlineCompanyFactory, \
    DSARegionFactory

from .factories import TravelFactory


class TresholdTest(APITenantTestCase):
    def setUp(self):
        super(TresholdTest, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)
        workspace = self.unicef_staff.profile.country
        workspace.threshold_tae_usd = 10
        workspace.threshold_tre_usd = 10
        workspace.save()

    def _prepare_test(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        return travel_id, data

    @override_settings(DISABLE_INVOICING=False)
    def test_threshold(self):
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], '120.00')

        # Treshold reached. Send for approval
        data = response_json
        data['expenses'][0]['amount'] = '300'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

    @override_settings(DISABLE_INVOICING=True)
    def test_threshold(self):
        travel_id, data = self._prepare_test()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], '120.00')

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], '120.00')

        # Treshold reached. Send for approval
        data = response_json
        data['expenses'][0]['amount'] = '300'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SENT_FOR_PAYMENT)
