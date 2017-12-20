from __future__ import unicode_literals

import json
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import (
    PublicsBusinessAreaFactory,
    PublicsCurrencyFactory,
    PublicsDSARegionFactory,
    PublicsTravelExpenseTypeFactory,
    PublicsWBSFactory,
)
from t2f.models import Invoice, ModeOfTravel, Travel
from t2f.tests.factories import TravelFactory
from users.tests.factories import UserFactory


class StateMachineTest(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory(is_staff=True)
        cls.traveler.profile.vendor_number = 'usrvend'
        cls.traveler.profile.save()

        cls.unicef_staff = UserFactory(is_staff=True)

    def test_possible_transitions(self):
        travel = TravelFactory()
        transition_mapping = defaultdict(list)
        for transition in list(travel._meta.get_field('status').get_all_transitions(travel.__class__)):
            transition_mapping[transition.source].append(transition.target)

        # mapping == {source: [target list]}
        self.assertEqual(dict(transition_mapping),
                         {'*': ['planned'],
                          'approved': ['sent_for_payment',
                                       'cancelled',
                                       'completed'],
                          'cancelled': ['submitted',
                                        'planned',
                                        'completed'],
                          'certification_approved': ['certification_rejected',
                                                     'certified'],
                          'certification_rejected': ['certification_submitted'],
                          'certification_submitted': ['certification_rejected',
                                                      'certification_approved'],
                          'certified': ['sent_for_payment',
                                        'certification_submitted',
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
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        wbs = PublicsWBSFactory(business_area=business_area)
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
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'currency': currency.id,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertIsNotNone(travel.submitted_at)
        self.assertIsNotNone(travel.first_submission_date)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=response_json, user=self.traveler)

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
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.CERTIFIED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, '')
        # None should be handled as empty string
        travel.report_note = None   # This has to be set explicitly since serializer does not accept None
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, None)

        data = response_json
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    @override_settings(DISABLE_INVOICING=True)
    def test_state_machine_flow_invoice_disabled(self):
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        wbs = PublicsWBSFactory(business_area=business_area)
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
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'currency': currency.id,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertIsNotNone(travel.submitted_at)
        self.assertIsNotNone(travel.first_submission_date)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        # Go straight to sent for payment when invoicing is disabled.
        self.assertEqual(response_json['status'], Travel.SENT_FOR_PAYMENT)

        # No email has been sent regarding SENT_FOR_PAYMENT status when invoicing is disabled.
        subjects = [x.subject for x in mail.outbox]
        self.assertNotIn('Travel #{} sent for payment.'.format(response_json["reference_number"]), subjects)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_certified'}),
                                        data=response_json, user=self.traveler)

        response_json = json.loads(response.rendered_content)
        # No pending invoice check when invoicing is disabled.
        self.assertEqual(response_json['status'], Travel.CERTIFIED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, '')

        # None should be handled as empty string
        travel.report_note = None   # This has to be set explicitly since serializer does not accept None
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, None)

        data = response_json
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_ta_not_required_flow_instant_complete(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'start_date': datetime.utcnow(),
                'report': 'something',
                'end_date': datetime.utcnow() + timedelta(hours=10),
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

        self.assertEqual(len(mail.outbox), 1)

    def test_ta_not_required_flow_send_for_approval(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'report': 'something',
                'start_date': datetime.utcnow(),
                'end_date': datetime.utcnow() + timedelta(hours=10),
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
                'report': 'something',
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
                'report': 'something',
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'mark_as_completed'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'non_field_errors': ["Transition conditions have not been met "
                                               "for method 'mark_as_completed'"]})

    def test_expense_required_on_send_for_payment(self):
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()
        currency = PublicsCurrencyFactory()

        wbs = PublicsWBSFactory(business_area=business_area)
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
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'expenses': [],
                'currency': currency.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=response_json, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response_json['cost_summary']['preserved_expenses']),
                         Decimal('0.00'))
