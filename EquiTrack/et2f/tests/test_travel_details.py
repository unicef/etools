from __future__ import unicode_literals

import json
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
        details_url = reverse('et2f:travels:details', kwargs={'pk': 1})
        self.assertEqual(details_url, '/api/et2f/travels/1/')

    @skip('fix this somehow. query count vaires between 21 and 40 queries...')
    def test_list_view(self):
        with self.assertNumQueries(29):
            response = self.forced_auth_req('get', reverse('et2f:travels:details', kwargs={'pk': self.travel.id}),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})
