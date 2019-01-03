import json
from io import StringIO

from django.urls import reverse

import factory
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.publics.models import DSARegion
from etools.applications.publics.tests.factories import (
    PublicsAirlineCompanyFactory,
    PublicsBusinessAreaFactory,
    PublicsCurrencyFactory,
    PublicsDSARegionFactory,
    PublicsTravelExpenseTypeFactory,
    PublicsWBSFactory,
)
from etools.applications.t2f.models import ModeOfTravel, Travel, TravelAttachment, TravelType
from etools.applications.t2f.tests.factories import TravelAttachmentFactory, TravelFactory
from etools.applications.users.tests.factories import UserFactory


class TravelDetails(URLAssertionMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory(
            code="t2f_travel_attachment"
        )
        cls.traveler = UserFactory(is_staff=True)
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('index', '', {'travel_pk': 1}),
            ('attachments', 'attachments/', {'travel_pk': 1}),
            ('attachment_details', 'attachments/1/', {'travel_pk': 1, 'attachment_pk': 1}),
            ('clone_for_driver', 'add_driver/', {'travel_pk': 1}),
            ('clone_for_secondary_traveler', 'duplicate_travel/', {'travel_pk': 1}),
        )
        self.assertReversal(names_and_paths, 't2f:travels:details:', '/api/t2f/travels/1/')
        self.assertIntParamRegexes(names_and_paths, 't2f:travels:details:')

        # Verify the many state change URLs.
        names = (Travel.SUBMIT_FOR_APPROVAL, Travel.APPROVE, Travel.REJECT, Travel.CANCEL, Travel.PLAN, Travel.COMPLETE)
        names_and_paths = (('state_change', name + '/', {'travel_pk': 1, 'transition_name': name}) for name in names)
        self.assertReversal(names_and_paths, 't2f:travels:details:', '/api/t2f/travels/1/')
        self.assertIntParamRegexes(names_and_paths, 't2f:travels:details:')

    def test_details_view(self):
        with self.assertNumQueries(23):
            response = self.forced_auth_req('get', reverse('t2f:travels:details:index',
                                                           kwargs={'travel_pk': self.travel.id}),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertKeysIn(['cancellation_note', 'supervisor', 'attachments', 'office', 'expenses', 'ta_required',
                           'completed_at', 'certification_note', 'misc_expenses', 'traveler', 'id', 'additional_note',
                           'section', 'clearances', 'cost_assignments', 'start_date', 'status', 'activities',
                           'rejection_note', 'end_date', 'mode_of_travel', 'international_travel',
                           'first_submission_date', 'deductions', 'purpose', 'report', 'itinerary',
                           'reference_number', 'cost_summary', 'currency', 'canceled_at', 'estimated_travel_cost'],
                          response_json,
                          exact=True)

    def test_details_view_with_file(self):
        attachment = TravelAttachmentFactory(
            travel=self.travel,
            name=u'\u0628\u0631\u0646\u0627\u0645\u062c \u062a\u062f\u0631\u064a\u0628 \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u064a\u0646.pdf',  # noqa
            file=factory.django.FileField(filename=u'travels/lebanon/24800/\u0628\u0631\u0646\u0627\u0645\u062c_\u062a\u062f\u0631\u064a\u0628_\u0627\u0644\u0645\u062a\u0627\u0628\u0639\u064a\u0646.pdf')  # noqa
        )
        with self.assertNumQueries(24):
            response = self.forced_auth_req(
                'get',
                reverse('t2f:travels:details:index', args=[self.travel.pk]),
                user=self.unicef_staff
            )
        response_json = json.loads(response.rendered_content)

        self.assertKeysIn(
            ['cancellation_note', 'supervisor', 'attachments', 'office', 'expenses', 'ta_required',
             'completed_at', 'certification_note', 'misc_expenses', 'traveler', 'id', 'additional_note',
             'section', 'clearances', 'cost_assignments', 'start_date', 'status', 'activities',
             'rejection_note', 'end_date', 'mode_of_travel', 'international_travel', 'itinerary',
             'first_submission_date', 'deductions', 'purpose', 'report',
             'reference_number', 'cost_summary', 'currency', 'canceled_at', 'estimated_travel_cost'],
            response_json,
            exact=True
        )
        self.assertEqual(len(response_json['attachments']), 1)
        self.assertEqual(response_json['attachments'][0]["id"], attachment.pk)

    def test_details_view_with_attachment(self):
        attachment = TravelAttachmentFactory(
            travel=self.travel,
        )
        AttachmentFactory(
            file="test_file.pdf",
            file_type=self.file_type,
            code="t2f_travel_attachment",
            content_object=attachment,
        )
        with self.assertNumQueries(25):
            response = self.forced_auth_req(
                'get',
                reverse('t2f:travels:details:index', args=[self.travel.pk]),
                user=self.unicef_staff
            )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['attachments']), 1)
        self.assertEqual(response_json['attachments'][0]["id"], attachment.pk)

    def test_travel_attachment(self):
        attachment = TravelAttachmentFactory(travel=self.travel)
        response = self.forced_auth_req(
            'get',
            reverse('t2f:travels:details:attachments', args=[self.travel.pk]),
            user=self.unicef_staff
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assertKeysIn(
            ['id', 'name', 'type', 'url', 'file', 'attachment'],
            response_json[0],
            exact=True
        )
        self.assertEqual(response_json[0]["id"], attachment.pk)

    def test_travel_attachment_nonascii(self):
        attachment = TravelAttachmentFactory(
            travel=self.travel,
            name=u'\u0628\u0631\u0646\u0627\u0645\u062c \u062a\u062f\u0631\u064a\u0628 \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u064a\u0646.pdf',  # noqa
            file=factory.django.FileField(filename=u'travels/lebanon/24800/\u0628\u0631\u0646\u0627\u0645\u062c_\u062a\u062f\u0631\u064a\u0628_\u0627\u0644\u0645\u062a\u0627\u0628\u0639\u064a\u0646.pdf')  # noqa
        )
        response = self.forced_auth_req(
            'get',
            reverse('t2f:travels:details:attachments', args=[self.travel.pk]),
            user=self.unicef_staff
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assertKeysIn(
            ['id', 'name', 'type', 'url', 'file', 'attachment'],
            response_json[0],
            exact=True
        )
        self.assertEqual(response_json[0]["id"], attachment.pk)

    def test_file_attachments(self):
        class FakeFile(StringIO):
            def size(self):
                return len(self)

        fakefile = FakeFile('some stuff')
        travel = TravelFactory()
        attachment = TravelAttachment.objects.create(travel=travel,
                                                     name='test_attachment',
                                                     type='document')
        attachment.file.save('fake.txt', fakefile)
        self.assertGreater(len(fakefile.getvalue()), 0)
        fakefile.seek(0)

        data = {'name': 'second',
                'type': 'something',
                'file': fakefile}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:attachments',
                                                        kwargs={'travel_pk': travel.id}),
                                        data=data, user=self.unicef_staff, request_format='multipart')
        response_json = json.loads(response.rendered_content)

        expected_keys = ['file', 'id', 'name', 'type', 'url', 'attachment']
        self.assertKeysIn(expected_keys, response_json)

        response = self.forced_auth_req('delete', reverse('t2f:travels:details:attachment_details',
                                                          kwargs={'travel_pk': travel.id,
                                                                  'attachment_pk': response_json['id']}),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 204)

    def test_add_attachment(self):
        travel = TravelFactory()
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        attachment_qs = TravelAttachment.objects.filter(
            travel=travel
        )
        self.assertFalse(attachment_qs.exists())
        data = {
            'name': 'second',
            'type': 'something',
            'attachment': attachment.pk,
        }
        response = self.forced_auth_req(
            'post',
            reverse(
                't2f:travels:details:attachments',
                kwargs={'travel_pk': travel.pk}
            ),
            data=data,
            user=self.unicef_staff,
            request_format='multipart',
        )
        response_json = json.loads(response.rendered_content)

        expected_keys = ['file', 'id', 'name', 'type', 'url', 'attachment']
        self.assertKeysIn(expected_keys, response_json)
        self.assertTrue(attachment_qs.exists())

    def test_patch_request(self):
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()

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
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['expenses'][0]['currency'], response_json['expenses'][0]['document_currency'])
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        data = {'expenses': response_json['expenses']}
        data['expenses'].append({'amount': '200',
                                 'type': expense_type.id,
                                 'currency': currency.id,
                                 'document_currency': currency.id})
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': travel_id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['deductions']), 1)

    def test_duplication(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_driver',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

        cloned_travel = Travel.objects.get(id=response_json['id'])
        self.assertNotEqual(cloned_travel.reference_number, self.travel.reference_number)

        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_secondary_traveler',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

    def test_airlines(self):
        dsaregion = DSARegion.objects.first()
        airlines_1 = PublicsAirlineCompanyFactory()
        airlines_2 = PublicsAirlineCompanyFactory()
        airlines_3 = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.PLANE,
                               'airlines': [airlines_1.id, airlines_2.id]}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        data = response_json
        data['itinerary'][0]['airlines'] = [airlines_1.id, airlines_3.id]
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': travel_id}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(sorted(response_json['itinerary'][0]['airlines']), sorted([airlines_1.id, airlines_3.id]))

    def test_preserved_expenses(self):
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'cost_assignments': [],
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
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.APPROVE}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

    def test_detailed_expenses(self):
        currency = PublicsCurrencyFactory()
        user_et = PublicsTravelExpenseTypeFactory(vendor_number='user')
        travel_agent_1_et = PublicsTravelExpenseTypeFactory(vendor_number='ta1')
        travel_agent_2_et = PublicsTravelExpenseTypeFactory(vendor_number='ta2')
        parking_money_et = PublicsTravelExpenseTypeFactory(vendor_number='')

        data = {'cost_assignments': [],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'ta_required': True,
                'expenses': [{'amount': '120',
                              'type': user_et.id,
                              'currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '80',
                              'type': user_et.id,
                              'currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '100',
                              'type': travel_agent_1_et.id,
                              'currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '500',
                              'type': travel_agent_2_et.id,
                              'currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '1000',
                              'type': parking_money_et.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['expenses'],
                         [{'amount': '120.00',
                           'currency': currency.id,
                           'label': user_et.title,
                           'vendor_number': 'Traveler'},
                          {'amount': '80.00',
                           'currency': currency.id,
                           'label': user_et.title,
                           'vendor_number': 'Traveler'},
                          {'amount': '100.00',
                           'currency': currency.id,
                           'label': travel_agent_1_et.title,
                           'vendor_number': 'ta1'},
                          {'amount': '500.00',
                           'currency': currency.id,
                           'label': travel_agent_2_et.title,
                           'vendor_number': 'ta2'},
                          {'amount': '1000.00',
                           'currency': currency.id,
                           'label': parking_money_et.title,
                           'vendor_number': ''}])

    def test_cost_assignments(self):
        wbs = PublicsWBSFactory()
        grant = wbs.grants.first()
        fund = grant.funds.first()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'fund': fund.id,
                                      'grant': grant.id,
                                      'share': 55}],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'cost_assignments': ['Shares should add up to 100%']})

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'fund': fund.id,
                                      'grant': grant.id,
                                      'share': 100,
                                      'business_area': business_area.id,
                                      'delegate': False}],
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
                'ta_required': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertKeysIn(['wbs', 'fund', 'grant', 'share', 'business_area', 'delegate'],
                          response_json['cost_assignments'][0])

    def test_activity_location(self):
        location = LocationFactory()
        location_2 = LocationFactory()
        location_3 = LocationFactory()

        data = {'cost_assignments': [],
                'activities': [{'is_primary_traveler': True,
                                'locations': [location.id, location_2.id]}],
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.traveler)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['activities'].append({'locations': [location_3.id],
                                   'is_primary_traveler': True})
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': response_json['id']}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        self.assertCountEqual(response_json['activities'][0]['locations'], [location.id, location_2.id])
        self.assertEqual(response_json['activities'][1]['locations'], [location_3.id])

    def test_activity_results(self):
        location = LocationFactory()
        location_2 = LocationFactory()

        data = {'cost_assignments': [],
                'activities': [{
                    'is_primary_traveler': True,
                    'locations': [location.id, location_2.id],
                    'partner': PartnerFactory(partner_type=PartnerType.GOVERNMENT).id,
                    'travel_type': TravelType.PROGRAMME_MONITORING,
                }],
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.traveler)

        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {u'activities': [{u'result': [u'This field is required.']}]})

    def test_itinerary_dates(self):
        dsaregion = DSARegion.objects.first()
        airlines = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Itinerary items have to be ordered by date']})

    def test_itinerary_submit_fail(self):
        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [],
                'activities': []}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.traveler)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'non_field_errors': ['Travel must have at least two itinerary item']})

    def test_itinerary_origin_destination(self):
        dsaregion = DSARegion.objects.first()
        airlines = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Something else',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'supervisor': self.unicef_staff.id,
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Origin should match with the previous destination']})

    def test_itinerary_dsa_regions(self):
        dsaregion = DSARegion.objects.first()
        airlines = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': None,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'non_field_errors': ['All itinerary items has to have DSA region assigned']})

        # Non ta trip
        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': None,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'supervisor': self.unicef_staff.id,
                'ta_required': False}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

    def test_activity_locations(self):
        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [],
                'activities': [{}],
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff, expected_status_code=None)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'activities': [{'primary_traveler': ['This field is required.']}]})

    def test_reversed_itinerary_order(self):
        dsa_1 = DSARegion.objects.first()
        dsa_2 = PublicsDSARegionFactory()

        data = {'itinerary': [{'airlines': [],
                               'origin': 'a',
                               'destination': 'b',
                               'dsa_region': dsa_1.id,
                               'departure_date': '2017-01-18T23:00:01.224Z',
                               'arrival_date': '2017-01-19T23:00:01.237Z',
                               'mode_of_travel': 'car'},
                              {'origin': 'b',
                               'destination': 'c',
                               'dsa_region': dsa_2.id,
                               'departure_date': '2017-01-20T23:00:01.892Z',
                               'arrival_date': '2017-01-27T23:00:01.905Z',
                               'mode_of_travel': 'car'}],
                'activities': [{'is_primary_traveler': True,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [],
                'action_points': [],
                'ta_required': True,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        itinerary_origin_destination_expectation = [('a', 'b'), ('b', 'c')]
        extracted_origin_destination = [(i['origin'], i['destination']) for i in response_json['itinerary']]
        self.assertEqual(extracted_origin_destination, itinerary_origin_destination_expectation)

    def test_incorrect_itinerary_order(self):
        dsa_1 = DSARegion.objects.first()
        dsa_2 = PublicsDSARegionFactory()

        data = {
            'itinerary': [
                {
                    'airlines': [],
                    'origin': 'b',
                    'destination': 'c',
                    'dsa_region': dsa_1.id,
                    'departure_date': '2017-01-20T23:00:01.892Z',
                    'arrival_date': '2017-01-27T23:00:01.905Z',
                    'mode_of_travel': 'car'
                },
                {
                    'origin': 'a',
                    'destination': 'b',
                    'dsa_region': dsa_2.id,
                    'departure_date': '2017-01-18T23:00:01.224Z',
                    'arrival_date': '2017-01-19T23:00:01.237Z',
                    'mode_of_travel': 'car'
                }
            ],
            'activities': [
                {
                    'is_primary_traveler': True,
                    'locations': []
                }
            ],
            'cost_assignments': [],
            'expenses': [],
            'action_points': [],
            'ta_required': True,
            'international_travel': False,
            'traveler': self.traveler.id,
            'mode_of_travel': []
        }

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        itinerary_origin_destination_expectation = [u'Origin should match with the previous destination']
        self.assertEqual(response_json['itinerary'], itinerary_origin_destination_expectation)

    def test_ta_not_required(self):
        data = {'itinerary': [],
                'activities': [{'is_primary_traveler': True,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [{}],
                'action_points': [],
                'ta_required': False,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        # Check only if 200
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)

    def test_not_primary_traveler(self):
        primary_traveler = UserFactory()

        data = {'itinerary': [],
                'activities': [{'is_primary_traveler': False,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [{}],
                'action_points': [],
                'ta_required': False,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'activities': [{'primary_traveler': ['This field is required.']}]})

        data = {'itinerary': [],
                'activities': [{'is_primary_traveler': False,
                                'primary_traveler': primary_traveler.id,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [{}],
                'action_points': [],
                'ta_required': False,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)

    def test_missing_clearances(self):
        data = {'itinerary': [],
                'activities': [{'is_primary_traveler': True,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [],
                'action_points': [],
                'ta_required': True,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        # Check only if 200
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)

        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=response_json['id'])
        travel.clearances.delete()

        response = self.forced_auth_req('put', reverse('t2f:travels:details:index',
                                                       kwargs={'travel_pk': response_json['id']}),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

    def test_travel_activity_partnership(self):
        partnership = InterventionFactory()

        data = {'itinerary': [],
                'activities': [{'is_primary_traveler': True,
                                'locations': [],
                                'partnership': partnership.id}],
                'cost_assignments': [],
                'expenses': [],
                'action_points': [],
                'ta_required': True,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        # Check only if 200
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)

        response_json = json.loads(response.rendered_content)
        activity = response_json['activities'][0]

        self.assertEqual(activity['partnership'], partnership.id)

    def test_ghost_data_existence(self):
        dsa_region = DSARegion.objects.first()
        airline = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.PLANE,
                               'airlines': [airline.id]}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        travel_id = response_json['id']

        airline.delete()

        response = self.forced_auth_req('get', reverse('t2f:travels:details:index',
                                                       kwargs={'travel_pk': travel_id}),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['itinerary'][0]['airlines'], [airline.id])

    def test_save_with_ghost_data(self):
        dsa_region = DSARegion.objects.first()
        airline = PublicsAirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.PLANE,
                               'airlines': [airline.id]}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        travel_id = response_json['id']

        airline.delete()

        response = self.forced_auth_req('put', reverse('t2f:travels:details:index',
                                                       kwargs={'travel_pk': travel_id}),
                                        data=response_json,
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
