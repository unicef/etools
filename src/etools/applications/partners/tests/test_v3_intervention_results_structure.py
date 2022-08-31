from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestAPIInterventionRetrieveResultsStructure(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])
        self.intervention = InterventionFactory(
            status=Intervention.DRAFT, unicef_court=True,
            start=date(year=1970, month=1, day=1),
            end=date(year=1970, month=12, day=31),
        )

        self.partner_focal_point = UserFactory(realms__data=[])
        self.staff_member = PartnerStaffFactory(
            partner=self.intervention.agreement.partner,
            user=self.partner_focal_point,
        )
        self.intervention.partner_focal_points.add(self.staff_member)
        self.intervention.unicef_focal_points.add(self.user)

        self.result_link = InterventionResultLinkFactory(
            intervention=self.intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)
        self.retrieve_url = reverse(
            'partners:intervention-detail-results-structure',
            args=[self.intervention.pk]
        )

    def test_retrieve(self):
        quarter = self.intervention.quarters.first()

        activity1 = InterventionActivityFactory(result=self.pd_output)
        InterventionActivityItemFactory(activity=activity1, unicef_cash=8)
        quarter.activities.add(activity1)

        activity2 = InterventionActivityFactory(result=self.pd_output)
        InterventionActivityItemFactory(activity=activity2, unicef_cash=8)
        InterventionActivityItemFactory(activity=activity2, unicef_cash=8)
        quarter.activities.add(activity2)

        response = self.forced_auth_req(
            'get', self.retrieve_url,
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["result_links"]), 1)

        links = response.data["result_links"][0]
        self.assertIn("total", links)
        self.assertEqual(len(links["ll_results"]), 1)
        self.assertEqual(len(links["ll_results"][0]['activities']), 2)
        for actual_activity, expected_activity in zip(links["ll_results"][0]['activities'],
                                                      [activity1, activity2]):
            self.assertEqual(actual_activity['id'], expected_activity.pk)
            self.assertEqual(actual_activity['is_active'], expected_activity.is_active)
            for field in ['name', 'code', 'context_details',
                          'unicef_cash', 'cso_cash']:
                self.assertEqual(actual_activity[field], str(getattr(expected_activity, field)))

            self.assertEqual(len(actual_activity['items']), expected_activity.items.count())
            for actual_item, expected_item in zip(actual_activity['items'],
                                                  expected_activity.items.all()):
                for field in ['name', 'unit', 'unit_price', 'no_units',
                              'unicef_cash', 'cso_cash']:
                    self.assertEqual(actual_item[field], str(getattr(expected_item, field)))

    def test_retrieve_no_result_activities(self):
        response = self.forced_auth_req(
            'get', self.retrieve_url,
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["result_links"]), 1)

        links = response.data["result_links"][0]
        self.assertIn("total", links)
        self.assertEqual(len(links["ll_results"]), 1)
        self.assertEqual(len(links["ll_results"][0]['activities']), 0)
