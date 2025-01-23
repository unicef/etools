import datetime
import json
from collections import defaultdict
from unittest.mock import Mock, patch

from django.conf import settings
from django.core import mail
from django.urls import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import (
    PublicsBusinessAreaFactory,
    PublicsCurrencyFactory,
    PublicsDSARegionFactory,
)
from etools.applications.t2f.models import ModeOfTravel, Travel
from etools.applications.t2f.serializers.mailing import TravelMailSerializer
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.users.tests.factories import UserFactory


class StateMachineTest(BaseTenantTestCase):
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
        expected = {'*': ['planned'],
                    'approved': ['cancelled',
                                 'completed'],
                    'cancelled': ['submitted',
                                  'planned',
                                  'completed'],
                    'planned': ['submitted',
                                'cancelled',
                                'completed'],
                    'rejected': ['submitted',
                                 'planned',
                                 'cancelled'],
                    'submitted': ['rejected',
                                  'cancelled',
                                  'approved',
                                  'completed']}

        self.assertCountEqual(expected.keys(), transition_mapping.keys())
        for key in expected:
            self.assertCountEqual(expected[key], transition_mapping[key])

    def test_state_machine_flow(self):
        currency = PublicsCurrencyFactory()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'currency': currency.id,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=travel_id)
        self.assertIsNotNone(travel.submitted_at)
        self.assertIsNotNone(travel.first_submission_date)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.APPROVE}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['status'], Travel.APPROVED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, '')
        # None should be handled as empty string
        travel.report_note = None   # This has to be set explicitly since serializer does not accept None
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, None)

        # data = response_json
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_state_machine_flow2(self):
        currency = PublicsCurrencyFactory()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'currency': currency.id,
                'supervisor': self.unicef_staff.id,
                }
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

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
        self.assertEqual(response_json['status'], Travel.APPROVED)

        # No email has been sent regarding SENT_FOR_PAYMENT status when invoicing is disabled.
        subjects = [x.subject for x in mail.outbox]
        self.assertNotIn('Travel #{} sent for payment.'.format(response_json["reference_number"]), subjects)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, '')

        # None should be handled as empty string
        travel.report_note = None   # This has to be set explicitly since serializer does not accept None
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['non_field_errors'], ['Field report has to be filled.'])
        self.assertEqual(travel.report_note, None)

        data = response_json
        data['report'] = 'Something'
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.COMPLETE}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

    def test_ta_not_required_flow_instant_complete(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'start_date': datetime.date.today(),
                'report': 'something',
                'end_date': datetime.date.today() + datetime.timedelta(days=1),
                'supervisor': self.unicef_staff.id}
        mock_send = Mock()
        with patch("etools.applications.t2f.models.send_notification", mock_send):
            response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                            kwargs={'transition_name': Travel.COMPLETE}),
                                            data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.COMPLETED)

        self.assertEqual(mock_send.call_count, 1)

    def test_ta_not_required_flow_send_for_approval(self):
        data = {'traveler': self.traveler.id,
                'ta_required': False,
                'international_travel': False,
                'report': 'something',
                'start_date': datetime.date.today(),
                'end_date': datetime.date.today() + datetime.timedelta(days=1),
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': Travel.REJECT}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=response_json, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': Travel.COMPLETE}),
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
                                                                'transition_name': Travel.COMPLETE}),
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
                                                        kwargs={'transition_name': Travel.COMPLETE}),
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

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'currency': currency.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

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
        self.assertEqual(response.status_code, 200)

    def test_cancel_notification(self):
        travel = TravelFactory(
            traveler=self.unicef_staff,
            supervisor=self.unicef_staff,
            status=Travel.APPROVED,
        )
        self.assertEqual(travel.status, Travel.APPROVED)
        mock_send = Mock()
        with patch("etools.applications.t2f.models.send_notification", mock_send):
            self.forced_auth_req(
                'post',
                reverse(
                    't2f:travels:details:state_change',
                    kwargs={
                        'travel_pk': travel.pk,
                        'transition_name': Travel.CANCEL,
                    },
                ),
                user=self.unicef_staff,
            )
        mock_send.assert_called_with(
            recipients=[
                travel.traveler.email,
                travel.supervisor.email,
            ],
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject='Travel #{} was cancelled.'.format(
                travel.reference_number,
            ),
            html_content_filename='emails/cancelled.html',
            context={
                "travel": TravelMailSerializer(travel, context={}).data,
                "url": travel.get_object_url(),
            }
        )
