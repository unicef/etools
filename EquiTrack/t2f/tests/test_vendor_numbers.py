
import json

from django.core.urlresolvers import reverse
from factory.fuzzy import FuzzyText

from EquiTrack.tests.cases import BaseTenantTestCase
from publics.tests.factories import TravelAgentFactory
from users.tests.factories import UserFactory


class VendorNumbers(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        vendor_numbers_list = reverse('t2f:vendor_numbers')
        self.assertEqual(vendor_numbers_list, '/api/t2f/vendor_numbers/')

    def test_vendor_number_list_view(self):
        for i in range(3):
            user = UserFactory(is_staff=True)
            user.first_name = 'Test'
            user.save()

            profile = user.profile
            profile.vendor_number = FuzzyText().fuzz()
            profile.save()

        for i in range(3):
            TravelAgentFactory()

        with self.assertNumQueries(2):
            response = self.forced_auth_req('get', reverse('t2f:vendor_numbers'), user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 6)
