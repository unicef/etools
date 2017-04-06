from __future__ import unicode_literals

import json
from collections import defaultdict

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import BusinessAreaFactory, WBSFactory
from t2f.models import Travel, Invoice
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory

from .factories import TravelFactory


class StateMachineTest(APITenantTestCase):
    def setUp(self):
        super(StateMachineTest, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_possible_transitions(self):
        travel = TravelFactory()
        transition_mapping = defaultdict(list)
        for transition in list(travel._meta.get_field('status').get_all_transitions(travel.__class__)):
            transition_mapping[transition.source].append(transition.target)

        # mapping == {source: [target list]}
        self.assertEqual(dict(transition_mapping),
                         {'*': ['planned'],
                          'approved': ['sent_for_payment',
                                       'cancelled'],
                          'cancelled': ['submitted', 'planned'],
                          'certification_approved': ['certification_rejected',
                                                     'certified'],
                          'certification_rejected': ['certification_submitted'],
                          'certification_submitted': ['certification_rejected',
                                                      'certification_approved'],
                          'certified': ['sent_for_payment',
                                        'cancelled',
                                        'completed'],
                          'planned': ['submitted',
                                      'cancelled',
                                      'completed'],
                          'rejected': ['submitted',
                                       'planned',
                                       'cancelled'],
                          'sent_for_payment': ['sent_for_payment',
                                               'submitted',
                                               'certified',
                                               'certification_submitted',
                                               'cancelled'],
                          'submitted': ['rejected',
                                        'cancelled',
                                        'approved',
                                        'completed']})

    def test_state_machine_flow(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()
        business_area = BusinessAreaFactory()

        wbs = WBSFactory(business_area=business_area)
        grant = wbs.grants.first()
        fund = grant.funds.first()

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

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, '')

        # None should be handled as empty string
        travel.report_note = None   # This has to be set explicitly since serializer does not accept None
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, None)

        data = response_json
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_ta_not_required_flow_instant_complete(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_ta_not_required_flow_send_for_approval(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'reject'}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'submit_for_approval'}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'mark_as_completed'}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_international_travel(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'mark_as_completed'}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

        # Try to complete an international travel instantly
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'non_field_errors': ["Transition conditions have not been met "
                                               "for method 'mark_as_completed'"]})
