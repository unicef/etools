import json
import os
from django.core.urlresolvers import reverse
from rest_framework import status
from EquiTrack.tests.mixins import APITenantTestCase
from partners.tests.test_utils import setup_intervention_test_data


class TestInterventionsAPI(APITenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        super(TestInterventionsAPI, self).setUp()
        setup_intervention_test_data(self)

    def run_prp_v1(self, user=None, method='get'):
        response = self.forced_auth_req(
            method,
            reverse('prp_api_v1:prp-intervention-list'),
            user=user or self.unicef_staff,
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_prp_api(self):
        with self.assertNumQueries(22):
            status_code, response = self.run_prp_v1(
                user=self.unicef_staff, method='get'
            )

        self.assertEqual(status_code, status.HTTP_200_OK)

        print json.dumps(response, indent=2)
        json_filename = os.path.join(os.path.dirname(__file__), 'data', 'prp-intervention-list.json')
        with open(json_filename) as f:
            expected_intervention = json.loads(f.read())

        for dynamic_key in ['id', 'number']:
            for result in response:
                del result[dynamic_key]
            for result in expected_intervention:
                del result[dynamic_key]

        self.assertEqual(response, expected_intervention)
