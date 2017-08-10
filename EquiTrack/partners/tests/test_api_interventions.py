from __future__ import unicode_literals

import json
import datetime
from unittest import skip, TestCase

from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework import status

from EquiTrack.factories import (
    PartnerFactory,
    UserFactory,
    ResultFactory,
    AgreementFactory,
    InterventionFactory,
    FundsReservationHeaderFactory,
    GroupFactory)
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from reports.models import ResultType, Sector
from partners.models import (
    InterventionSectorLocationLink,
    InterventionBudget,
    InterventionAmendment,
    Intervention
)


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
            ('intervention-sector-locations-del', 'sector-locations/1/', {'pk': 1}),
            ('intervention-map', 'map/', {}),
            )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/interventions/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestInterventionsAPI(APITenantTestCase):
    fixtures = ['initial_data.json']
    EDITABLE_FIELDS = {
        'draft': ["status", "sector_locations", "attachments", "prc_review_document", 'travel_activities',
                  "partner_authorized_officer_signatory", "partner_focal_points", "distributions", "id",
                  "country_programme", "amendments", "unicef_focal_points", "end", "title",
                  "signed_by_partner_date", "review_date_prc", "target_actions", "frs", "start", "supplies",
                  "metadata", "submission_date", "action_object_actions", "agreement", "unicef_signatory_id",
                  "result_links", "contingency_pd", "unicef_signatory", "agreement_id", "signed_by_unicef_date",
                  "partner_authorized_officer_signatory_id", "actor_actions", "created", "planned_visits",
                  "planned_budget", "modified", "signed_pd_document", "submission_date_prc", "document_type",
                  "offices", "population_focus", "country_programme_id", "engagement"],
        'signed': [],
        'active': ['']
    }
    REQUIRED_FIELDS = {
        'draft': ['number', 'title', 'agreement', 'document_type'],
        'signed': [],
        'active': ['']
    }
    ALL_FIELDS = Intervention._meta.get_all_field_names()

    def setUp(self):
        today = datetime.date.today()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())
        self.partner = PartnerFactory()
        self.partner1 = PartnerFactory()
        self.agreement = AgreementFactory(partner=self.partner, signed_by_unicef_date=datetime.date.today())

        self.active_agreement = AgreementFactory(partner=self.partner1,
                                                 status='active',
                                                 signed_by_unicef_date=datetime.date.today(),
                                                 signed_by_partner_date=datetime.date.today())

        self.intervention = InterventionFactory(agreement=self.agreement)
        self.intervention_2 = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD)
        self.active_intervention = InterventionFactory(agreement=self.active_agreement,
                                                       document_type=Intervention.PD,
                                                       start=today - datetime.timedelta(days=1),
                                                       end=today + datetime.timedelta(days=90),
                                                       status='active',
                                                       signed_by_unicef_date=today - datetime.timedelta(days=1),
                                                       signed_by_partner_date=today - datetime.timedelta(days=1),
                                                       unicef_signatory=self.unicef_staff,
                                                       partner_authorized_officer_signatory=self.partner1.
                                                       staff_members.all().first())

        self.result_type = ResultType.objects.get(name=ResultType.OUTPUT)
        self.result = ResultFactory(result_type=self.result_type)

        self.pcasector = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 1")
        )
        self.partnership_budget = InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention,
            types=[InterventionAmendment.RESULTS]
        )
        self.location = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 2")
        )
        # set up two frs not connected to any interventions
        self.fr_1 = FundsReservationHeaderFactory(intervention=None)
        self.fr_2 = FundsReservationHeaderFactory(intervention=None)

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
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.rendered_content)
        self.assertEqual(result.get('result_links'), {'name': ['This field may not be null.']})

    def test_add_one_valid_fr_on_create_pd(self):
        frs_data = [self.fr_1.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_add_two_valid_frs_on_create_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)

    def test_fr_details_is_accurate_on_creation(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEquals(response['frs_details']['total_actual_amt'],
                          float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEquals(response['frs_details']['total_outstanding_amt'],
                          float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEquals(response['frs_details']['total_frs_amt'],
                          float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
        self.assertEquals(response['frs_details']['total_intervention_amt'],
                          float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))

    def test_add_two_valid_frs_on_update_pd(self):
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response['frs'], frs_data)
        self.assertEquals(response['frs_details']['total_actual_amt'],
                          float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
        self.assertEquals(response['frs_details']['total_outstanding_amt'],
                          float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
        self.assertEquals(response['frs_details']['total_frs_amt'],
                          float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
        self.assertEquals(response['frs_details']['total_intervention_amt'],
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
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch', user=self.unicef_staff)

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
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in draft: title', response)

    def test_permissions_for_intervention_status_draft(self):
        # intervention is in Draft status
        self.assertEquals(self.intervention.status, Intervention.DRAFT)

        # user is UNICEF User
        status_code, response = self.run_request(self.intervention.id, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        # all fields are there
        self.assertItemsEqual(self.ALL_FIELDS, response['permissions']['edit'].keys())
        edit_permissions = response['permissions']['edit']
        required_permissions = response['permissions']['required']
        self.assertItemsEqual(self.EDITABLE_FIELDS['draft'],
                              [perm for perm in edit_permissions if edit_permissions[perm]])
        self.assertItemsEqual(self.REQUIRED_FIELDS['draft'],
                              [perm for perm in required_permissions if required_permissions[perm]])

    @skip('add test after permissions file is ready')
    def test_permissions_for_intervention_status_active(self):
        # intervention is in Draft status
        self.assertEquals(self.active_intervention.status, Intervention.ACTIVE)

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
        with self.assertNumQueries(10):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEquals(len(response), 3)

        # add another intervention to make sure that the queries are constant
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
        }
        status_code, response = self.run_request_list_ep(data)
        self.assertEqual(status_code, status.HTTP_201_CREATED)

        # even though we added a new intervention, the number of queries remained static
        with self.assertNumQueries(10):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEquals(len(response), 4)
