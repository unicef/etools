import datetime
import json
import os

from django.urls import resolve, reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIRequestFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import WorkspaceRequiredAPITestMixIn
from etools.applications.locations.tests.factories import GatewayTypeFactory, LocationFactory
from etools.applications.partners.models import InterventionResultLink, PartnerOrganization
from etools.applications.partners.permissions import READ_ONLY_API_GROUP_NAME
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.partners.tests.test_utils import setup_intervention_test_data
from etools.applications.reports.models import AppliedIndicator, IndicatorBlueprint, LowerResult
from etools.applications.reports.tests.factories import ResultFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestInterventionsAPI(WorkspaceRequiredAPITestMixIn, BaseTenantTestCase):
    def setUp(self):
        super(TestInterventionsAPI, self).setUp()
        setup_intervention_test_data(self, include_results_and_indicators=True)

    def run_prp_v1(self, user=None, method='get', data=None):
        response = self.forced_auth_req(
            method,
            reverse('prp_api_v1:prp-intervention-list'),
            user=user or self.unicef_staff,
            data=data,
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_prp_partners_v1(self, user=None, method='get', data=None):
        response = self.forced_auth_req(
            method,
            reverse('prp_api_v1:prp-partner-list'),
            user=user or self.unicef_staff,
            data=data,
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_prp_api(self):
        status_code, response = self.run_prp_v1(
            user=self.unicef_staff, method='get'
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        response = response['results']

        # uncomment if you need to see the response json / regenerate the test file
        # print(json.dumps(response, indent=2))
        # TODO: think of how to improve this test without having to dig through the object to delete ids
        json_filename = os.path.join(os.path.dirname(__file__), 'data', 'prp-intervention-list.json')
        with open(json_filename) as f:
            expected_interventions = json.loads(f.read())

        # need to do some annoying scrubbing of IDs
        for i in range(len(response)):
            expected_intervention = expected_interventions[i]
            actual_intervention = response[i]
            for dynamic_key in ['id', 'number', 'start_date', 'end_date', 'update_date']:
                del expected_intervention[dynamic_key]
                del actual_intervention[dynamic_key]

            partner_org = PartnerOrganization.objects.get(id=actual_intervention['partner_org']['id'])
            expected_intervention['partner_org']['unicef_vendor_number'] = partner_org.vendor_number
            del actual_intervention['partner_org']['id']
            del actual_intervention['agreement']
            del expected_intervention['partner_org']['id']
            del expected_intervention['agreement']
            del expected_intervention['partner_org']['unicef_vendor_number']
            del actual_intervention['partner_org']['unicef_vendor_number']

            for j in range(len(expected_intervention['expected_results'])):
                del expected_intervention['expected_results'][j]['id']
                del expected_intervention['expected_results'][j]['cp_output']['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['blueprint_id']
                del expected_intervention['expected_results'][j]['indicators'][0]['disaggregation'][0]['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['locations'][0]['id']
                del expected_intervention['expected_results'][j]['indicators'][0]['locations'][0]['admin_level']

                del actual_intervention['expected_results'][j]['id']
                del actual_intervention['expected_results'][j]['result_link']
                del actual_intervention['expected_results'][j]['cp_output']['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['blueprint_id']
                del actual_intervention['expected_results'][j]['indicators'][0]['disaggregation'][0]['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['locations'][0]['id']
                del actual_intervention['expected_results'][j]['indicators'][0]['locations'][0]['admin_level']

        self.assertEqual(response, expected_interventions)

    def test_prp_partners_api(self):
        status_code, response = self.run_prp_partners_v1(
            user=self.unicef_staff, method='get'
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        response = response['results']
        self.assertEqual(len(response), 2)

    def test_prp_api_modified_queries(self):
        yesterday = (timezone.now() - datetime.timedelta(days=1)).isoformat()
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).isoformat()
        checks = [
            ({'updated_before': yesterday}, 0),
            ({'updated_before': tomorrow}, 3),
            ({'updated_after': yesterday}, 3),
            ({'updated_after': tomorrow}, 0),
            ({'updated_before': tomorrow, 'updated_after': yesterday}, 3),
        ]
        for params, expected_results in checks:
            status_code, response = self.run_prp_v1(
                user=self.unicef_staff, method='get', data=params
            )
            self.assertEqual(status_code, status.HTTP_200_OK)
            self.assertEqual(expected_results, len(response['results']))

    def test_prp_api_performance(self):
        EXPECTED_QUERIES = 24
        with self.assertNumQueries(EXPECTED_QUERIES):
            self.run_prp_v1(
                user=self.unicef_staff, method='get'
            )
        # make a bunch more stuff, make sure queries don't go up.
        intervention = InterventionFactory(agreement=self.agreement, title='New Intervention')
        result = ResultFactory(name='Another Result')
        result_link = InterventionResultLink.objects.create(
            intervention=intervention, cp_output=result)
        lower_result = LowerResult.objects.create(result_link=result_link, name='Lower Result 1')
        indicator_blueprint = IndicatorBlueprint.objects.create(
            title='The Blueprint'
        )
        applied_indicator = AppliedIndicator.objects.create(
            indicator=indicator_blueprint,
            lower_result=lower_result,
        )
        applied_indicator.locations.add(LocationFactory(name='A Location',
                                                        gateway=GatewayTypeFactory(name='Another Gateway'),
                                                        p_code='a-p-code'))
        applied_indicator.disaggregation.create(name='Another Disaggregation')
        with self.assertNumQueries(EXPECTED_QUERIES):
            self.run_prp_v1(
                user=self.unicef_staff, method='get'
            )


class TestInterventionsAPIListPermissions(BaseTenantTestCase):
    '''Exercise permissions on the PRPIntervention list view'''

    @classmethod
    def setUpTestData(cls):
        cls.readonly_group = GroupFactory(name=READ_ONLY_API_GROUP_NAME)

    def setUp(self):
        self.url = reverse('prp_api_v1:prp-intervention-list')
        self.query_param_data = {'workspace': self.tenant.business_area_code}

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self.forced_auth_req('get', self.url, user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_member_has_access(self):
        '''Ensure a non-staff user in the correct group has access'''
        user = UserFactory()
        user.groups.add(self.readonly_group)
        response = self.forced_auth_req('get', self.url, user=user, data=self.query_param_data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_staff_has_access(self):
        '''Ensure a staff user has access'''
        response = self.forced_auth_req('get', self.url, user=UserFactory(is_staff=True), data=self.query_param_data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
