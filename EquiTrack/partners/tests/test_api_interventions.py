from __future__ import unicode_literals

import json
import datetime
from unittest import skip, TestCase

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.urlresolvers import reverse, resolve
from django.db import connection
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIRequestFactory

from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from EquiTrack.factories import (
    AgreementFactory,
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    IndicatorFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    InterventionResultLinkFactory,
    InterventionSectorLocationLinkFactory,
    LocationFactory,
    LowerResultFactory,
    PartnerFactory,
    ResultFactory,
    SectorFactory,
    UserFactory)
from environment.helpers import tenant_switch_is_active
from environment.models import TenantSwitch
from environment.tests.factories import TenantSwitchFactory
from partners.tests.test_utils import setup_intervention_test_data
from partners.models import (
    Intervention,
    InterventionAmendment,
    InterventionResultLink,
)
from snapshot.models import Activity
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
            ('intervention-indicators', 'indicators/', {}),
            ('intervention-results', 'results/', {}),
            ('intervention-results-del', 'results/1/', {'pk': 1}),
            ('intervention-amendments', 'amendments/', {}),
            ('intervention-amendments-del', 'amendments/1/', {'pk': 1}),
            ('intervention-sector-locations', 'sector-locations/', {}),
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
                  "signed_by_partner_date", "review_date_prc", "frs", "start",
                  "metadata", "submission_date", "agreement", "unicef_signatory_id",
                  "result_links", "contingency_pd", "unicef_signatory", "agreement_id", "signed_by_unicef_date",
                  "partner_authorized_officer_signatory_id", "created", "planned_visits",
                  "planned_budget", "modified", "signed_pd_document", "submission_date_prc", "document_type",
                  "offices", "population_focus", "country_programme_id", "engagement", "sections",
                  "sections_present", "flat_locations"],
        'signed': [],
        'active': ['']
    }
    REQUIRED_FIELDS = {
        'draft': ['number', 'title', 'agreement', 'document_type'],
        'signed': [],
        'active': ['']
    }
    ALL_FIELDS = get_all_field_names(Intervention) + ['sections_present']

    def setUp(self):
        setup_intervention_test_data(self)

    def tearDown(self):
        cache.delete("public-intervention-permissions")
        if hasattr(self, "ts"):
            self.ts.delete()

    def run_request_list_ep(self, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-list'),
            user=user or self.unicef_staff,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request_list_dash_ep(self, data={}, user=None, method='get'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-list-dash'),
            user=user or self.unicef_staff,
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
        self.assertFalse(Activity.objects.exists())
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
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention.pk]
            ),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.rendered_content)
        self.assertEqual(result.get('result_links'), {'name': ['This field may not be null.']})
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            0
        )

    def test_dashboard_list_focal_point(self):
        self.active_intervention.unicef_focal_points.add(self.unicef_staff)
        status_code, response = self.run_request_list_dash_ep()
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 1)
        self.draft_intervention = InterventionFactory(agreement=self.agreement,
                                                      status='draft')
        self.draft_intervention.unicef_focal_points.add(self.unicef_staff)
        status_code, response = self.run_request_list_dash_ep()
        self.assertEqual(len(response), 1)

    def test_dashboard_list_partnership_manager(self):
        self.draft_intervention = InterventionFactory(agreement=self.agreement,
                                                      status='draft')
        status_code, response = self.run_request_list_dash_ep(user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4)

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
        self.assertFalse(Activity.objects.exists())
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
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_two_valid_frs_on_create_pd(self):
        self.assertFalse(Activity.objects.exists())
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
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_fr_details_is_accurate_on_creation(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.vendor_code = self.agreement.partner.vendor_number
        self.fr_2.vendor_code = self.agreement.partner.vendor_number
        self.fr_1.save()
        self.fr_2.save()
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
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_two_valid_frs_on_update_pd(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.vendor_code = self.intervention_2.agreement.partner.vendor_number
        self.fr_2.vendor_code = self.intervention_2.agreement.partner.vendor_number
        self.fr_1.save()
        self.fr_2.save()
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
        self.assertTrue(Activity.objects.exists())
        activity = Activity.objects.first()
        self.assertEqual(activity.target, self.intervention_2)
        self.assertEqual(activity.action, Activity.UPDATE)
        self.assertIn("frs", activity.change)
        frs = activity.change["frs"]
        self.assertEqual(frs["before"], [])
        self.assertItemsEqual(frs["after"], [self.fr_1.pk, self.fr_2.pk])
        self.assertEqual(activity.by_user, self.partnership_manager_user)

    def test_remove_an_fr_from_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

        # Remove fr_1
        frs_data = [self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            2
        )

    def test_fail_add_expired_fr_on_pd(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.end_date = timezone.now().date() - datetime.timedelta(days=1)
        self.fr_1.save()

        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertTrue(Activity.objects.exists())

    def test_fail_add_used_fr_on_pd(self):
        self.assertFalse(Activity.objects.exists())
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
        self.assertFalse(Activity.objects.exists())

    def test_add_same_frs_twice_on_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertTrue(Activity.objects.exists())

        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEqual(Activity.objects.all().count(), 2)

    def test_patch_title_fail_as_unicef_user(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "title": 'Changed Title'
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Activity.objects.exists())

    def test_permissions_for_intervention_status_draft(self):

        # TODO: this tests only with PRP mode on. PRP mode off tests needed here.
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

        section1 = SectorFactory()
        section2 = SectorFactory()

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

    def test_list_interventions_w_flag(self):
        self.ts = TenantSwitchFactory(name="prp_mode_off", countries=[connection.tenant])
        self.assertTrue(tenant_switch_is_active(self.ts.name))

        EXPECTED_QUERIES = 10
        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 3)

        section1 = SectorFactory()
        section2 = SectorFactory()
        EXTRA_INTERVENTIONS = 15
        for i in range(0, EXTRA_INTERVENTIONS + 1):
            intervention = InterventionFactory(
                document_type=Intervention.PD,
                start=(timezone.now().date()).isoformat(),
                end=(timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
                agreement=self.agreement,
            )
            intervention.sections.add(section1.pk)
            intervention.sections.add(section2.pk)

        self.assertEqual(Intervention.objects.count(), 4 + EXTRA_INTERVENTIONS)

        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4 + EXTRA_INTERVENTIONS)


class TestAPIInterventionResultLinkListView(APITenantTestCase):
    '''Exercise the list view for InterventionResultLinkListCreateView'''
    def setUp(self):
        self.intervention = InterventionFactory()

        self.result_link1 = InterventionResultLinkFactory(intervention=self.intervention)
        self.result_link2 = InterventionResultLinkFactory(intervention=self.intervention)

        self.url = reverse('partners_api:intervention-result-links-list',
                           kwargs={'intervention_pk': self.intervention.id})

        # self.expected_field_names is the list of field names expected in responses.
        self.expected_field_names = sorted((
            'cp_output',
            'ram_indicators',
            'cp_output_name',
            'ram_indicator_names',
            'id',
            'intervention',
            'created',
            'modified',
        ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        '''Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
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
        response = self._make_request(UserFactory())
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
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        '''A non-staff user has read access if in the correct group'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
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

    def _make_request(self, user):
        return self.forced_auth_req('post', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
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
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkRetrieveView(APITenantTestCase):
    '''Exercise the retrieve view for InterventionResultLinkUpdateView'''
    def setUp(self):
        self.intervention_result_link = InterventionResultLinkFactory()

        self.url = reverse('partners_api:intervention-result-links-update',
                           kwargs={'pk': self.intervention_result_link.id})

        # self.expected_keys are the keys expected in a JSON response.
        self.expected_keys = sorted((
            'cp_output',
            'ram_indicators',
            'cp_output_name',
            'ram_indicator_names',
            'id',
            'intervention',
            'created',
            'modified',
        ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(self.expected_keys, sorted(response_json.keys()))

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        '''Ensure a staff user can access'''
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission_non_staff(self):
        '''Ensure group membership is sufficient for retrieval; even non-staff group members can retrieve'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkUpdateView(APITenantTestCase):
    '''Exercise the update view for InterventionResultLinkUpdateView'''
    def setUp(self):
        self.intervention_result_link = InterventionResultLinkFactory()

        self.url = reverse('partners_api:intervention-result-links-update',
                           kwargs={'pk': self.intervention_result_link.id})

        self.new_cp_output = ResultFactory()

        self.data = {'cp_output': self.new_cp_output.id}

    def _make_request(self, user):
        return self.forced_auth_req('patch', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        intervention_result_link = InterventionResultLink.objects.get(pk=self.intervention_result_link.id)
        self.assertEqual(intervention_result_link.cp_output.id, self.new_cp_output.id)

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.patch(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_refused(self):
        '''Ensure a staff doesn't have write access'''
        response = self._make_request(UserFactory(is_staff=True))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        '''Ensure group membership is sufficient for update; even non-staff group members can update'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkDeleteView(APITenantTestCase):
    '''Exercise the delete view for InterventionResultLinkUpdateView'''
    def setUp(self):
        self.intervention_result_link = InterventionResultLinkFactory()

        self.url = reverse('partners_api:intervention-result-links-update',
                           kwargs={'pk': self.intervention_result_link.id})

    def _make_request(self, user):
        return self.forced_auth_req('delete', self.url, user=user)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InterventionResultLink.objects.filter(pk=self.intervention_result_link.id).exists())

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.patch(self.url, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_refused(self):
        '''Ensure a staff doesn't have write access'''
        response = self._make_request(UserFactory(is_staff=True))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        '''Ensure group membership is sufficient for update; even non-staff group members can update'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionLowerResultListView(APITenantTestCase):
    '''Exercise the list view for InterventionLowerResultListCreateView'''
    @classmethod
    def setUpClass(cls):
        super(TestAPIInterventionLowerResultListView, cls).setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        cls.lower_result1 = LowerResultFactory(result_link=cls.result_link)
        cls.lower_result2 = LowerResultFactory(result_link=cls.result_link)

        # Create another result link/lower result pair that will break this test if the views don't filter properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-lower-results-list',
                          kwargs={'result_link_pk': cls.result_link.id})

        # cls.expected_field_names is the list of field names expected in responses.
        cls.expected_field_names = sorted(('id', 'code', 'created', 'modified', 'name', 'result_link'))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        '''Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
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
        expected_ids = sorted((self.lower_result1.id, self.lower_result2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
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
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        '''A non-staff user has read access if in the correct group'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionLowerResultCreateView(APITenantTestCase):
    '''Exercise the create view for InterventionLowerResultListCreateView'''
    @classmethod
    def setUpClass(cls):
        super(TestAPIInterventionLowerResultCreateView, cls).setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        # Create another result link/lower result pair that will break this test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-lower-results-list',
                          kwargs={'result_link_pk': cls.result_link.id})

        cls.data = {'name': 'my lower result'}

    def _make_request(self, user):
        return self.forced_auth_req('post', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())
        # The id of the newly-created lower result should be associated with my result link, and it should be
        # the only one associated with that result link.
        self.assertEqual([response_json['id']],
                         [lower_result.id for lower_result in self.result_link.ll_results.all()])
        self.assertEqual(response_json.get('name'), 'my lower result')

        return response_json

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
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
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)

    def test_code_read_only(self):
        '''Ensure lower_result.code can't be written'''
        user = UserFactory()
        _add_user_to_partnership_manager_group(user)
        data = self.data.copy()
        data['code'] = 'ZZZ'

        response = self.forced_auth_req('post', self.url, user=user, data=data)
        response_json = self.assertResponseFundamentals(response)

        self.assertNotEqual(response_json.get('code'), 'ZZZ')


class TestAPIInterventionIndicatorsListView(APITenantTestCase):
    '''Exercise the list view for InterventionIndicatorsListView (these are AppliedIndicator instances)'''
    @classmethod
    def setUpClass(cls):
        super(TestAPIInterventionIndicatorsListView, cls).setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        cls.lower_result = LowerResultFactory(result_link=cls.result_link)

        cls.indicator1 = AppliedIndicatorFactory(lower_result=cls.lower_result)
        cls.indicator2 = AppliedIndicatorFactory(lower_result=cls.lower_result)

        # Create another result link/lower result/indicator combo that will break this test if the views don't
        # filter properly
        AppliedIndicatorFactory(lower_result=LowerResultFactory(result_link=InterventionResultLinkFactory()))

        cls.url = reverse('partners_api:intervention-indicators-list',
                          kwargs={'lower_result_pk': cls.lower_result.id})

        # cls.expected_field_names is the list of field names expected in responses.
        cls.expected_field_names = sorted(('id', 'assumptions', 'baseline', 'cluster_indicator_id', 'cluster_name',
                                           'cluster_indicator_title', 'context_code', 'disaggregation',
                                           'indicator', 'locations', 'lower_result', 'means_of_verification',
                                           'section', 'target', 'total', 'created', 'modified', 'response_plan_name', ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        '''Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
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
        expected_ids = sorted((self.indicator1.id, self.indicator2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
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
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        '''A non-staff user has read access if in the correct group'''
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPInterventionIndicatorsCreateView(APITenantTestCase):
    '''Exercise the create view for InterventionIndicatorsListView (these are AppliedIndicator instances)'''
    @classmethod
    def setUpClass(cls):
        super(TestAPInterventionIndicatorsCreateView, cls).setUpClass()

        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)

        # Create another result link/lower result pair that will break this test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-indicators-list',
                          kwargs={'lower_result_pk': cls.lower_result.id})

        location = LocationFactory()
        section = SectorFactory()

        cls.result_link.intervention.flat_locations.add(location)
        cls.result_link.intervention.sections.add(section)

        cls.data = {'assumptions': 'lorem ipsum',
                    'locations': [location.id],
                    'section': section.id,
                    # indicator (blueprint) is required because the AppliedIndicator model has a unique_together
                    # constraint of (indicator, lower_result).
                    'indicator': {'title': 'my indicator blueprint'},
                    }

    def _make_request(self, user, data=None):
        if data is None:
            data = self.data
        return self.forced_auth_req('post', self.url, user=user, data=data)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())
        # The id of the newly-created indicator should be associated with my lower result, and it should be
        # the only one associated with that result.
        self.assertEqual([response_json['id']],
                         [indicator.id for indicator in self.lower_result.applied_indicators.all()])
        self.assertEqual(response_json.get('assumptions'), 'lorem ipsum')

        return response_json

    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self._make_request(UserFactory())
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
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)

    def test_multiple_association(self):
        '''Ensure a different indicator blueprint can be associated with the same lower_result, but
        the same indicator can't be added twice.
        '''
        user = UserFactory()
        _add_user_to_partnership_manager_group(user)
        data = self.data.copy()
        data['indicator'] = {'title': 'another indicator blueprint'}
        response = self._make_request(user, data)
        # OK to add a different indicator
        self.assertResponseFundamentals(response)

        response = self._make_request(user, data)
        # Adding the same indicator again should fail.
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json.keys(), ['non_field_errors'])
        self.assertIsInstance(response_json['non_field_errors'], list)
        self.assertEqual(response_json['non_field_errors'],
                         ['This indicator is already being monitored for this Result'])


class TestInterventionPlannedVisitsDeleteView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionPlannedVisitsDeleteView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = InterventionFactory()
        self.planned_visit = InterventionPlannedVisitsFactory(
            intervention=self.intervention,
        )
        self.url = reverse(
            "partners_api:intervention-visits-del",
            args=[self.planned_visit.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a planned visit"])

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-visits-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInterventionAttachmentDeleteView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionAttachmentDeleteView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = InterventionFactory()
        self.attachment = InterventionAttachmentFactory(
            intervention=self.intervention,
            attachment="random_attachment.pdf",
        )
        self.url = reverse(
            "partners_api:intervention-attachments-del",
            args=[self.attachment.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = "active"
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an attachment"])

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-attachments-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInterventionResultListAPIView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionResultListAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        InterventionResultLinkFactory()
        self.intervention = InterventionFactory()
        self.result = ResultFactory(
            name="Result Name",
            code="Result Code",
        )
        self.link = InterventionResultLinkFactory(
            intervention=self.intervention,
            cp_output=self.result
        )
        self.url = reverse("partners_api:intervention-results")

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)

    def test_search_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_cp_output_name(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "Name"}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_cp_output_code(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "Code"}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)


class TestInterventionIndicatorListAPIView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionIndicatorListAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        InterventionResultLinkFactory()
        self.intervention = InterventionFactory()
        self.indicator = IndicatorFactory()
        self.link = InterventionResultLinkFactory(
            intervention=self.intervention,
        )
        self.link.ram_indicators.add(self.indicator)
        self.url = reverse("partners_api:intervention-indicators")

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('intervention', first.keys())
        return response_json, first

    def test_search(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["intervention"], self.intervention.pk)

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)


class TestInterventionResultLinkDeleteView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionResultLinkDeleteView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = InterventionFactory()
        self.result = InterventionResultLinkFactory(
            intervention=self.intervention,
        )
        self.url = reverse(
            "partners_api:intervention-results-del",
            args=[self.result.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a result"])

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-results-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInterventionAmendmentListAPIView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionAmendmentListAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        InterventionAmendmentFactory()
        self.intervention = InterventionFactory()
        self.amendment = InterventionAmendmentFactory(
            intervention=self.intervention,
            amendment_number="321",
        )
        self.url = reverse("partners_api:intervention-amendments")

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_search_intervention_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.amendment.pk)

    @skip("fix count issue")
    def test_search_amendment_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.amendment.amendment_number}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.amendment.pk)

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)


class TestInterventionAmendmentDeleteView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionAmendmentDeleteView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = InterventionFactory()
        self.amendment = InterventionAmendmentFactory(
            intervention=self.intervention,
            types=[InterventionAmendment.RESULTS],
            signed_date=datetime.date.today(),
            signed_amendment="random_amendment.pdf"
        )
        self.url = reverse(
            "partners_api:intervention-amendments-del",
            args=[self.amendment.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an amendment"])

    def test_intervention_amendments_delete(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-amendments-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInterventionSectorLocationLinkListAPIView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionSectorLocationLinkListAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        InterventionSectorLocationLinkFactory()
        self.intervention = InterventionFactory()
        self.sector = SectorFactory(name="Sector Name")
        self.link = InterventionSectorLocationLinkFactory(
            intervention=self.intervention,
            sector=self.sector
        )
        self.url = reverse("partners_api:intervention-sector-locations")

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_search_intervention_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_sector_name(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "Name"}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)


class TestInterventionListMapView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionListMapView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.url = reverse("partners_api:intervention-map")
        self.intervention = InterventionFactory(status=Intervention.DRAFT)

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response.'''
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.intervention.pk)

    def test_get_param_country_programme(self):
        country_programme = CountryProgrammeFactory()
        agreement = AgreementFactory(country_programme=country_programme)
        intervention = InterventionFactory(agreement=agreement)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"country_programme": country_programme.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)

    def test_get_param_section_wo_flag(self):
        # make sure there is no prp_mode_off flag.. this serves to flush the cache
        ts = TenantSwitch.get('prp_mode_off')
        # since the cache is extremely unreliable as tests progress this is something to go around that
        if ts.id:
            ts.delete()
        sector = SectorFactory()
        intervention = InterventionFactory()
        rl = InterventionResultLinkFactory(intervention=intervention)
        llo = LowerResultFactory(result_link=rl)
        AppliedIndicatorFactory(lower_result=llo, section=sector)

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"section": sector.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)

    def test_get_param_section_with_flag(self):
        # set prp mode off flag
        TenantSwitchFactory(name='prp_mode_off', countries=[connection.tenant])
        sector = SectorFactory()
        intervention = InterventionFactory()
        intervention.sections.add(sector)

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"section": sector.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)

    def test_get_param_status(self):
        InterventionFactory(status=Intervention.ACTIVE)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"status": self.intervention.status},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.intervention.pk)

    def test_get_param_partner(self):
        partner = PartnerFactory()
        agreement = AgreementFactory(partner=partner)
        intervention = InterventionFactory(agreement=agreement)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"partner": partner.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)
