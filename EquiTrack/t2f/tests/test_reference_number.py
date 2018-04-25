
import json

from django.core.urlresolvers import reverse
from freezegun import freeze_time

from EquiTrack.tests.cases import BaseTenantTestCase
from users.tests.factories import UserFactory


class TestReferenceNumber(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def _create_travel(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        return response_json

    @freeze_time('2016-12-09')
    def test_reference_number_increase(self):
        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/1')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/2')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/3')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/4')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/5')

    def test_year_change(self):
        with freeze_time('2016-12-09'):
            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2016/1')

            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2016/2')

        with freeze_time('2017-01-01'):
            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2017/3')

            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2017/4')
