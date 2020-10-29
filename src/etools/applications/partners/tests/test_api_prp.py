import datetime
import json
import os

from django.urls import resolve, reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIRequestFactory
from unicef_locations.tests.factories import GatewayTypeFactory, LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import WorkspaceRequiredAPITestMixIn
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import (
    Intervention,
    InterventionBudget,
    InterventionResultLink,
    PartnerOrganization,
)
from etools.applications.partners.permissions import READ_ONLY_API_GROUP_NAME
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.partners.tests.test_utils import setup_intervention_test_data
from etools.applications.reports.models import AppliedIndicator, IndicatorBlueprint, LowerResult, ResultType
from etools.applications.reports.tests.factories import ReportingRequirementFactory, ResultFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory
from etools.libraries.tests.api_checker import ApiCheckerMixin, AssertTimeStampedMixin


class TestInterventionsAPI(WorkspaceRequiredAPITestMixIn, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
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
            del expected_intervention['reporting_requirements']
            del actual_intervention['reporting_requirements']

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
            ({'updated_before': tomorrow}, 1),
            ({'updated_after': yesterday}, 1),
            ({'updated_after': tomorrow}, 0),
            ({'updated_before': tomorrow, 'updated_after': yesterday}, 1),
        ]
        for params, expected_results in checks:
            status_code, response = self.run_prp_v1(
                user=self.unicef_staff, method='get', data=params
            )
            self.assertEqual(status_code, status.HTTP_200_OK)
            self.assertEqual(expected_results, len(response['results']))

    def test_prp_api_performance(self):
        EXPECTED_QUERIES = 25
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
    """Exercise permissions on the PRPIntervention list view"""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_group = GroupFactory(name=READ_ONLY_API_GROUP_NAME)

    def setUp(self):
        self.url = reverse('prp_api_v1:prp-intervention-list')
        self.query_param_data = {'workspace': self.tenant.business_area_code}

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self.forced_auth_req('get', self.url, user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_member_has_access(self):
        """Ensure a non-staff user in the correct group has access"""
        user = UserFactory()
        user.groups.add(self.readonly_group)
        response = self.forced_auth_req('get', self.url, user=user, data=self.query_param_data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_staff_has_access(self):
        """Ensure a staff user has access"""
        response = self.forced_auth_req('get', self.url, user=UserFactory(is_staff=True), data=self.query_param_data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)


class TestAPIPRP(ApiCheckerMixin, AssertTimeStampedMixin, WorkspaceRequiredAPITestMixIn, BaseTenantTestCase):

    def assert_results(self, response, expected, path=''):
        extepted_results = json.loads(json.dumps(expected['results'][0]))
        response_results = json.loads(json.dumps(response['results'][0]))
        assert sorted(response_results.keys()) == sorted(extepted_results.keys())

    def get_fixtures(self):
        today = datetime.date.today()

        partnership_user = UserFactory(is_staff=True, email='partner@unicef.org')
        partnership_user.groups.add(GroupFactory())

        partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
        partner1 = PartnerFactory(name='Partner 2')
        agreement = AgreementFactory(partner=partner, signed_by_unicef_date=datetime.date.today())
        active_agreement = AgreementFactory(
            partner=partner1,
            status='active',
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today())
        unicef_staff = UserFactory(is_staff=True, email='staff@unicef.org')
        result_type = ResultType.objects.get_or_create(name=ResultType.OUTPUT)[0]
        intervention = InterventionFactory(agreement=agreement, title='Intervention 1')
        active_intervention = InterventionFactory(
            agreement=active_agreement, title='Active Intervention',
            document_type=Intervention.PD, start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=90),
            status='active',
            submission_date=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=unicef_staff,
            partner_authorized_officer_signatory=partner1.staff_members.all().first()
        )
        result = ResultFactory(result_type=result_type)
        result_link = InterventionResultLink.objects.create(intervention=active_intervention, cp_output=result)
        indicator_blueprint = IndicatorBlueprint.objects.create(title='The Blueprint')
        lower_result = LowerResult.objects.create(result_link=result_link, name='Lower Result 1')
        applied_indicator = AppliedIndicator.objects.create(indicator=indicator_blueprint, lower_result=lower_result, )
        applied_indicator.locations.add(LocationFactory(
            name='A Location', gateway=GatewayTypeFactory(name='A Gateway'), p_code='a-p-code'))
        disaggregation = applied_indicator.disaggregation.create(name='A Disaggregation')

        return {
            "unicef_staff": unicef_staff,
            "partnership_manager_user": partnership_user,
            "partner": partner,
            "partner1": partner1,
            "agreement": agreement,
            "active_agreement": active_agreement,
            "intervention": intervention,
            "intervention_2": InterventionFactory(agreement=agreement, title='Intervention 2',
                                                  document_type=Intervention.PD),
            "active_intervention": active_intervention,
            "reporting_requirement": ReportingRequirementFactory(intervention=active_intervention),
            "result_type": result_type,
            "result": result,
            "partnership_budget": InterventionBudget.objects.create(
                intervention=intervention,
                unicef_cash=10,
                unicef_cash_local=100,
                partner_contribution=20,
                partner_contribution_local=200,
                in_kind_amount_local=10,
            ),
            "fr_1": FundsReservationHeaderFactory(intervention=None, currency='USD'),
            "fr_2": FundsReservationHeaderFactory(intervention=None, currency='USD'),
            "result_link": result_link,
            "lower_result": lower_result,
            "indicator_blueprint": indicator_blueprint,
            "applied_indicator": applied_indicator,
            "file_type_attachment": AttachmentFileTypeFactory(
                group=["partners_intervention_attachment"],
            ),
            "file_type_prc": AttachmentFileTypeFactory(
                group=["partners_intervention_prc_review"],
            ),
            "file_type_pd": AttachmentFileTypeFactory(
                group=["partners_intervention_signed_pd"],
            ),
            "disaggregation": disaggregation
        }

    def test_prp_api(self):
        url = reverse('prp_api_v1:prp-intervention-list')
        self.assertGET(url, data={'workspace': self.tenant.business_area_code})
