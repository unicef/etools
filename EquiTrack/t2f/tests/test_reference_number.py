from __future__ import unicode_literals

import json
from freezegun import freeze_time

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase



class TestReferenceNumber(APITenantTestCase):
    def setUp(self):
        super(TestReferenceNumber, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def _create_travel(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        return response_json

    @freeze_time('2016-12-09')
    def test_reference_number_increase(self):
        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/000001')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/000002')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/000003')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/000004')

        response_json = self._create_travel()
        self.assertEqual(response_json['reference_number'], '2016/000005')

    def test_year_change(self):
        with freeze_time('2016-12-09'):
            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2016/000001')

            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2016/000002')

        with freeze_time('2017-01-01'):
            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2017/000001')

            response_json = self._create_travel()
            self.assertEqual(response_json['reference_number'], '2017/000002')
