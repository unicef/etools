import json

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory
from EquiTrack.tests.mixins import APITenantTestCase


class CurrentUserTest(APITenantTestCase):

    def setUp(self):
        super(CurrentUserTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_curent_user_endpoint(self):
        response = self.forced_auth_req('get', '/api/et2f/me/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'full_name': u'',
                          'id': self.unicef_staff.id,
                          'roles': [u'Anyone']})
