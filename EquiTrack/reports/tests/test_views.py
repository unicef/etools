__author__ = 'achamseddine'

import random

from rest_framework import status

from reports.models import ResultType
from EquiTrack.factories import UserFactory, ResultFactory
from EquiTrack.factories import SectionFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestReportViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.result_type = ResultType.objects.get(id=random.choice([1,2,3]))
        self.result1 = ResultFactory(result_type=self.result_type)

        # Additional data to use in tests
        self.location1 = LocationFactory()
        self.location3 = LocationFactory()
        self.section1 = SectionFactory()
        self.section3 = SectionFactory()

    def test_api_resultstructures_list(self):
        response = self.forced_auth_req('get', '/api/reports/result-structures/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_resulttypes_list(self):
        response = self.forced_auth_req('get', '/api/reports/result-types/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_sectors_list(self):
        response = self.forced_auth_req('get', '/api/reports/sectors/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_indicators_list(self):
        response = self.forced_auth_req('get', '/api/reports/indicators/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_results_list(self):
        response = self.forced_auth_req('get', '/api/reports/results/', user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(int(response.data[0]["id"]), self.result1.id)

    def test_api_results_patch(self):
        url = '/api/reports/results/{}/'.format(self.result1.id)
        data = {"name": "patched name"}
        response = self.forced_auth_req('patch', url, user=self.unicef_staff, data=data)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["name"], "patched name")

    def test_api_units_list(self):
        response = self.forced_auth_req('get', '/api/reports/units/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
