__author__ = 'achamseddine'

from rest_framework import status

from EquiTrack.factories import UserFactory, ResultFactory, LocationFactory, SectionFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestReportViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.location1 = LocationFactory()
        self.location2 = LocationFactory()
        self.section1 = SectionFactory()
        self.section2 = SectionFactory()
        self.result1 = ResultFactory(
                            geotag=[self.location1,self.location2],
                            users=[self.unicef_staff.profile.id],
                            sections=[self.section1,self.section2]
                        )

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

    def test_api_units_list(self):
        response = self.forced_auth_req('get', '/api/reports/units/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
