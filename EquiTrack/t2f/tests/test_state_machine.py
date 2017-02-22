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
from t2f.models import TravelAttachment, Travel, ModeOfTravel, Invoice
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, FundFactory, AirlineCompanyFactory, \
    DSARegionFactory

from .factories import TravelFactory


class StateMachineTest(APITenantTestCase):
    def setUp(self):
        super(StateMachineTest, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_state_machine_flow(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()
        business_area = BusinessAreaFactory()

        fund = FundFactory()
        grant = fund.grant
        wbs = grant.wbs
        wbs.business_area = business_area
        wbs.save()

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'grant': grant.id,
                                      'fund': fund.id,
                                      'share': 100}],
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

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Your TA has pending payments to be processed through '
                                                             'VISION. Until payments are completed, you can not certify'
                                                             ' your TA. Please check with your Finance focal point on '
                                                             'how to proceed.'])

        travel = Travel.objects.get(id=travel_id)
        travel.invoices.all().update(status=Invoice.SUCCESS)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.CERTIFIED)
