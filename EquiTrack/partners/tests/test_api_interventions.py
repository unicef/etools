from __future__ import unicode_literals

import json
import datetime
from unittest import skip, TestCase

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse, resolve
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIRequestFactory

from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from partners.tests.test_utils import setup_intervention_test_data
from partners.models import (
    Intervention
)
from users.models import Country
from EquiTrack.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    ResultFactory,
    SectionFactory,
    UserFactory,
)
from utils.common.utils import get_all_field_names


def _add_user_to_partnership_manager_group(user):
    '''Utility function to add a user to the 'Partnership Manager' group which may or may not exist'''
    group = Group.objects.get_or_create(name='Partnership Manager')[0]
    user.groups.add(group)


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('intervention-list', '', {}),
            ('intervention-list-dash', 'dash/', {}),
            ('intervention-detail', '1/', {'pk': 1}),
            ('intervention-visits-del', 'planned-visits/1/', {'pk': 1}),
            ('intervention-attachments-del', 'attachments/1/', {'pk': 1}),
            ('intervention-results-del', 'results/1/', {'pk': 1}),
            ('intervention-amendments-del', 'amendments/1/', {'pk': 1}),
            ('intervention-map', 'map/', {}),
            )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/interventions/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestInterventionsAPI(APITenantTestCase):
    fixtures = ['initial_data.json']
    EDITABLE_FIELDS = {
        'draft': ["status", "attachments", "prc_review_document", 'travel_activities',
                  "partner_authorized_officer_signatory", "partner_focal_points", "id",
                  "country_programme", "amendments", "unicef_focal_points", "end", "title",
                  "signed_by_partner_date", "review_date_prc", "target_actions", "frs", "start",
                  "metadata", "submission_date", "action_object_actions", "agreement", "unicef_signatory_id",
                  "result_links", "contingency_pd", "unicef_signatory", "agreement_id", "signed_by_unicef_date",
                  "partner_authorized_officer_signatory_id", "actor_actions", "created", "planned_visits",
                  "planned_budget", "modified", "signed_pd_document", "submission_date_prc", "document_type",
                  "offices", "population_focus", "country_programme_id", "engagement", "sections"],
        'signed': [],
        'active': ['']
    }
    REQUIRED_FIELDS = {
        'draft': ['number', 'title', 'agreement', 'document_type'],
        'signed': [],
        'active': ['']
    }
    ALL_FIELDS = get_all_field_names(Intervention)

    def setUp(self):
        setup_intervention_test_data(self)

    def run_request_list_ep(self, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-list'),
            user=user or self.unicef_staff,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request(self, intervention_id, data=None, method='get', user=None):
        user = user or self.partnership_manager_user
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-detail', kwargs={'pk': intervention_id}),
            user=user,
            data=data or {}
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_api_pd_output_not_populated(self):
        data = {
            "result_links": [
                {"cp_output": self.result.id,
                 # "ram_indicators": [152],
                 "ll_results": [
                     {"id": None, "name": None, "applied_indicators": []}
                 ]}]
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/' + str(self.intervention.id) + '/',
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.rendered_content)
        self.assertEqual(result.get('result_links'), {'name': ['This field may not be null.']})

    def test_add_contingency_pd(self):
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention1",
            "contingency_pd": True,
            "agreement": self.agreement.id,
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)

    def test_add_one_valid_fr_on_create_pd(self):
        frs_data = [self.fr_1.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_add_two_valid_frs_on_create_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_fr_details_is_accurate_on_creation(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEqual(response['frs_details']['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEqual(response['frs_details']['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEqual(response['frs_details']['total_frs_amt'],
                         float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
        self.assertEqual(response['frs_details']['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))

    def test_add_two_valid_frs_on_update_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEqual(response['frs_details']['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEqual(response['frs_details']['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEqual(response['frs_details']['total_frs_amt'],
                         float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
        self.assertEqual(response['frs_details']['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))

    def test_remove_an_fr_from_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)

        # Remove fr_1
        frs_data = [self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_fail_add_expired_fr_on_pd(self):
        self.fr_1.end_date = timezone.now().date() - datetime.timedelta(days=1)
        self.fr_1.save()

        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['frs'], ['One or more selected FRs is expired, {}'.format(self.fr_1.fr_number)])

    def test_fail_add_used_fr_on_pd(self):
        self.fr_1.intervention = self.intervention
        self.fr_1.save()

        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['frs'],
                         ['One or more of the FRs selected is related '
                          'to a different PD/SSFA, {}'.format(self.fr_1.fr_number)])

    def test_add_same_frs_twice_on_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)

        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_patch_title_fail_as_unicef_user(self):
        data = {
            "title": 'Changed Title'
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)

    def test_permissions_for_intervention_status_draft(self):
        # intervention is in Draft status
        self.assertEqual(self.intervention.status, Intervention.DRAFT)

        # user is UNICEF User
        status_code, response = self.run_request(self.intervention.id, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        # all fields are there
        self.assertItemsEqual(self.ALL_FIELDS, response['permissions']['edit'].keys())
        edit_permissions = response['permissions']['edit']
        required_permissions = response['permissions']['required']

        # TODO: REMOVE the following 3 lines after "sector_locations" are finally removed from the Intervention model
        # having sector_locations in the Intervention model and not having it in the permissions matrix fails this test
        del edit_permissions["sector_locations"]
        del required_permissions["sector_locations"]

        self.assertItemsEqual(self.EDITABLE_FIELDS['draft'],
                              [perm for perm in edit_permissions if edit_permissions[perm]])
        self.assertItemsEqual(self.REQUIRED_FIELDS['draft'],
                              [perm for perm in required_permissions if required_permissions[perm]])

    @skip('add test after permissions file is ready')
    def test_permissions_for_intervention_status_active(self):
        # intervention is in Draft status
        self.assertEqual(self.active_intervention.status, Intervention.ACTIVE)

        # user is UNICEF User
        status_code, response = self.run_request(self.active_intervention.id, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        # all fields are there
        self.assertItemsEqual(self.ALL_FIELDS, response['permissions']['edit'].keys())
        edit_permissions = response['permissions']['edit']
        required_permissions = response['permissions']['required']
        self.assertItemsEqual(self.EDITABLE_FIELDS['signed'],
                              [perm for perm in edit_permissions if edit_permissions[perm]])
        self.assertItemsEqual(self.REQUIRED_FIELDS['signed'],
                              [perm for perm in required_permissions if required_permissions[perm]])

    def test_list_interventions(self):
        EXPECTED_QUERIES = 10
        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 3)

        section1 = SectionFactory()
        Country.objects.get(schema_name="test").sections.add(section1)

        section2 = SectionFactory()
        Country.objects.get(schema_name="test").sections.add(section2)

        # add another intervention to make sure that the queries are constant
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "sections": [section1.id, section2.id],
        }

        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_201_CREATED)

        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4)


class TestAPIInterventionResultLinkListView(APITenantTestCase):
    '''Exercise the list view for InterventionResultLinkListCreateView'''
    def setUp(self):
        self.intervention = InterventionFactory()

        self.result_link1 = InterventionResultLinkFactory(intervention=self.intervention)
        self.result_link2 = InterventionResultLinkFactory(intervention=self.intervention)

        self.url = reverse('partners_api:intervention-result-links-list',
                           kwargs={'intervention_pk': self.intervention.id})

        # self.expected_field_names is the list of field names expected in responses.
        self.expected_field_names = sorted(
            ('cp_output', 'ram_indicators', 'cp_output_name', 'ram_indicator_names', 'id', 'intervention', ))

    def assertResponseFundamentals(self, response, expected_keys=None):
        '''Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.normal_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        '''
        if expected_keys is None:
            expected_keys = self.expected_field_names

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        for obj in response_json:
            self.assertIsInstance(obj, dict)
        if expected_keys:
            for d in response_json:
                self.assertEqual(sorted(d.keys()), expected_keys)

        actual_ids = sorted([d.get('id') for d in response_json])
        expected_ids = sorted((self.result_link1.id, self.result_link2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self.forced_auth_req('get', self.url, user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        '''Ensure a staff user has access'''
        response = self.forced_auth_req('get', self.url, user=UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        '''A non-staff user has read access if in the correct group'''
        user = UserFactory()
        _add_user_to_partnership_manager_group(user)
        response = self.forced_auth_req('get', self.url, user=user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkCreateView(APITenantTestCase):
    '''Exercise the create view for InterventionResultLinkListCreateView'''
    def setUp(self):
        self.intervention = InterventionFactory()

        self.url = reverse('partners_api:intervention-result-links-list',
                           kwargs={'intervention_pk': self.intervention.id})

        cp_output = ResultFactory()

        self.data = {'intervention_pk': self.intervention.id,
                     'cp_output': cp_output.id
                     }

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response. Return the id of the new object.'''
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self.forced_auth_req('post', self.url, data=self.data, user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        '''Ensure group membership is sufficient for create; even non-staff group members can create'''
        user = UserFactory()
        response = self.forced_auth_req('post', self.url, data=self.data, user=user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the create should succeed.
        response = self.forced_auth_req('post', self.url, data=self.data, user=user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkRetrieveView(APITenantTestCase):
    '''Exercise the retrieve view for InterventionResultLinkUpdateView'''
    def setUp(self):
        self.intervention_result_link = InterventionResultLinkFactory()

        self.url = reverse('partners_api:intervention-result-links-update',
                           kwargs={'pk': self.intervention_result_link.id})

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response. Return the id of the new object.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self.forced_auth_req('get', self.url, user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        '''Ensure a staff user can access'''
        response = self.forced_auth_req('get', self.url, user=UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission_non_staff(self):
        '''Ensure group membership is sufficient for create; even non-staff group members can create'''
        user = UserFactory()
        response = self.forced_auth_req('get', self.url, user=user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the get should succeed.
        response = self.forced_auth_req('get', self.url, user=user)
        self.assertResponseFundamentals(response)
