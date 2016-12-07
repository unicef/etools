from __future__ import unicode_literals

import json
from StringIO import StringIO
from unittest.case import skip

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from et2f.models import TravelAttachment

from .factories import TravelFactory


class TravelDetails(APITenantTestCase):
    def setUp(self):
        super(TravelDetails, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number='REF1',
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        details_url = reverse('et2f:travels:details:index', kwargs={'travel_pk': 1})
        self.assertEqual(details_url, '/api/et2f/travels/1/')

        attachments_url = reverse('et2f:travels:details:attachments', kwargs={'travel_pk': 1})
        self.assertEqual(attachments_url, '/api/et2f/travels/1/attachments/')

        attachment_details_url = reverse('et2f:travels:details:attachment_details',
                                         kwargs={'travel_pk': 1, 'attachment_pk': 1})
        self.assertEqual(attachment_details_url, '/api/et2f/travels/1/attachments/1/')

        add_driver_url = reverse('et2f:travels:details:clone_for_driver', kwargs={'travel_pk': 1})
        self.assertEqual(add_driver_url, '/api/et2f/travels/1/add_driver/')

        duplicate_travel_url = reverse('et2f:travels:details:clone_for_secondary_traveler', kwargs={'travel_pk': 1})
        self.assertEqual(duplicate_travel_url, '/api/et2f/travels/1/duplicate_travel/')

    @skip('fix this somehow. query count vaires between 21 and 40 queries...')
    def test_details_view(self):
        with self.assertNumQueries(29):
            response = self.forced_auth_req('get', reverse('et2f:travels:details:index',
                                                           kwargs={'travel_pk': self.travel.id}),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})

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
        fakefile.seek(0)

        data = {'name': 'second',
                'type': 'something',
                'file': fakefile}
        response = self.forced_auth_req('post', reverse('et2f:travels:details:attachments',
                                                        kwargs={'travel_pk': travel.id}),
                                        data=data, user=self.unicef_staff, request_format='multipart')
        response_json = json.loads(response.rendered_content)

        expected_keys = ['file', 'id', 'name', 'type', 'url']
        self.assertKeysIn(expected_keys, response_json)

        response = self.forced_auth_req('delete', reverse('et2f:travels:details:attachment_details',
                                                          kwargs={'travel_pk': travel.id,
                                                                  'attachment_pk': response_json['id']}),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 204)

    def test_duplication(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('et2f:travels:details:clone_for_driver',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('et2f:travels:details:clone_for_secondary_traveler',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)
