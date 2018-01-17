from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class SettingsView(APITenantTestCase):
    def setUp(self):
        super(SettingsView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        settings_url = reverse('t2f:settings')
        self.assertEqual(settings_url, '/api/t2f/settings/')

    def test_settings_view(self):
        response = self.forced_auth_req('get', reverse('t2f:settings'), user=self.unicef_staff)
        response_json = json.loads(response.rendered_content.decode('utf-8'))

        expected_keys = ['disable_invoicing']
        self.assertKeysIn(expected_keys, response_json)

    def test_disable_invoicing(self):
        response = self.forced_auth_req('get', reverse('t2f:settings'), user=self.unicef_staff)
        response_json = json.loads(response.rendered_content.decode('utf-8'))
        self.assertEqual(response_json, {'disable_invoicing': False})

        with override_settings(DISABLE_INVOICING=True):
            response = self.forced_auth_req('get', reverse('t2f:settings'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content.decode('utf-8'))
        self.assertEqual(response_json, {'disable_invoicing': True})
