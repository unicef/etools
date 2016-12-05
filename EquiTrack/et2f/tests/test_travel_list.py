from __future__ import unicode_literals

import json
import csv
from cStringIO import StringIO
from unittest.case import skip

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

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
        list_url = reverse('et2f:travels:list')
        self.assertEqual(list_url, '/api/et2f/travels/')
        list_export_url = reverse('et2f:travels:list_export')
        self.assertEqual(list_export_url, '/api/et2f/travels/export/')

    def test_list_view(self):
        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('et2f:travels:list'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)
        
        self.assertEqual(len(response_json['data']), 1)
        travel_data = response_json['data'][0]
        expected_keys = ['end_date', 'id', 'office', 'purpose', 'reference_number',
                         'section', 'start_date', 'status', 'traveler']
        self.assertKeysIn(expected_keys, travel_data)

    def test_export(self):
        response = self.forced_auth_req('get', reverse('et2f:travels:list_export'), user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['id',
                          'reference_number',
                          'traveler',
                          'purpose',
                          'start_date',
                          'end_date',
                          'status',
                          'created',
                          'section',
                          'office',
                          'supervisor',
                          'ta_required',
                          'ta_reference_number',
                          'approval_date',
                          'is_driver',
                          'attachment_count'])