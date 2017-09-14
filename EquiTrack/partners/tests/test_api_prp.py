import json
import os
from django.core.urlresolvers import reverse
from rest_framework import status
from EquiTrack.factories import ResultFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import InterventionResultLink
from partners.tests.test_utils import setup_intervention_test_data
from reports.models import LowerResult, AppliedIndicator, IndicatorBlueprint


class TestInterventionsAPI(APITenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        super(TestInterventionsAPI, self).setUp()
        setup_intervention_test_data(self)
        # setup data specific to PRP API
        self.result = ResultFactory()
        self.result_link = InterventionResultLink.objects.create(
            intervention=self.active_intervention, cp_output=self.result)
        self.lower_result = LowerResult.objects.create(result_link=self.result_link, name='Lower Result 1')
        self.indicator_blueprint = IndicatorBlueprint.objects.create(
            title='The Blueprint'
        )
        self.applied_indicator = AppliedIndicator.objects.create(
            indicator=self.indicator_blueprint,
            lower_result=self.lower_result,
        )
        self.applied_indicator.locations.add(LocationFactory(name='A Location'))
        self.applied_indicator.disaggregation.create(name='A Disaggregation')


    def run_prp_v1(self, user=None, method='get'):
        response = self.forced_auth_req(
            method,
            reverse('prp_api_v1:prp-intervention-list'),
            user=user or self.unicef_staff,
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_prp_api(self):
        # with self.assertNumQueries(22):
        status_code, response = self.run_prp_v1(
            user=self.unicef_staff, method='get'
        )

        self.assertEqual(status_code, status.HTTP_200_OK)

        print json.dumps(response, indent=2)
        json_filename = os.path.join(os.path.dirname(__file__), 'data', 'prp-intervention-list.json')
        with open(json_filename) as f:
            expected_interventions = json.loads(f.read())

        # need to do some annoying scrubbing of IDs
        for i in range(len(response)):
            expected_intervention = expected_interventions[i]
            actual_intervention = response[i]
            for dynamic_key in ['id', 'number']:
                del expected_intervention[dynamic_key]
                del actual_intervention[dynamic_key]
            for j in range(len(expected_intervention['expected_results'])):
                del expected_intervention['expected_results'][j]['id']
                del expected_intervention['expected_results'][j]['cp_output']['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['disaggregation'][0]['id']
                del actual_intervention['expected_results'][j]['id']
                del actual_intervention['expected_results'][j]['cp_output']['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['disaggregation'][0]['id']

        self.assertEqual(response, expected_interventions)
