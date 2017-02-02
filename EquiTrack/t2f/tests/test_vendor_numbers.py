from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

class VendorNumbers(APITenantTestCase):
    def setUp(self):
        super(VendorNumbers, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        vendor_numbers_list = reverse('t2f:vendor_numbers')
        self.assertEqual(vendor_numbers_list, '/api/t2f/vendor_numbers/')

    def test_vendor_number_list_view(self):
        response = self.forced_auth_req('get', reverse('t2f:vendor_numbers'), user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, [])
