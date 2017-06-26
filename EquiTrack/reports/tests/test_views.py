from unittest import skip
import datetime

from rest_framework import status

from reports.models import ResultType, CountryProgramme
from EquiTrack.factories import (
    UserFactory,
    ResultFactory,
    SectionFactory,
    LocationFactory,
    ResultStructureFactory,
    CountryProgrammeFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase


class TestReportViews(APITenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.result_type = ResultType.objects.get(name=ResultType.OUTPUT)
        self.result1 = ResultFactory(
            result_type=self.result_type,
            result_structure=ResultStructureFactory(),
            country_programme=CountryProgrammeFactory(wbs="/A0/"),
        )

        self.result2 = ResultFactory(
            result_type=self.result_type,
            result_structure=self.result1.result_structure,
            country_programme=self.result1.country_programme,
        )

        # Additional data to use in tests
        self.location1 = LocationFactory()
        self.location3 = LocationFactory()
        self.section1 = SectionFactory()
        self.section3 = SectionFactory()

    @skip("rename to hrp")
    def test_api_resultstructures_list(self):
        response = self.forced_auth_req('get', '/api/reports/result-structures/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_resulttypes_list(self):
        response = self.forced_auth_req('get', '/api/reports/result-types/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_sectors_list(self):
        response = self.forced_auth_req('get', '/api/reports/sectors/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_indicators_list(self):
        response = self.forced_auth_req('get', '/api/reports/indicators/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_results_list(self):
        response = self.forced_auth_req('get', '/api/reports/results/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_api_results_patch(self):
        url = '/api/reports/results/{}/'.format(self.result1.id)
        data = {"name": "patched name"}
        response = self.forced_auth_req('patch', url, user=self.unicef_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "patched name")

    def test_api_units_list(self):
        response = self.forced_auth_req('get', '/api/reports/units/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apiv2_results_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_minimal(self):
        params = {"verbosity": "minimal"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=params,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "name"])

    def test_apiv2_results_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/{}/'.format(self.result1.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data["id"]), self.result1.id)

    def test_apiv2_results_list_current_cp(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["country_programme"]), CountryProgramme.current().id)

    def test_apiv2_results_list_filter_year(self):
        param = {
            "year": datetime.date.today().year,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_apiv2_results_list_filter_cp(self):
        param = {
            "country_programme": self.result1.country_programme.id,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_filter_result_type(self):
        param = {
            "result_type": self.result_type.name,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_filter_values(self):
        param = {
            "values": '{},{}'.format(self.result1.id, self.result2.id)
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_apiv2_results_list_filter_values_bad(self):
        param = {
            "values": '{},{}'.format('23fg', 'aasd67')
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['ID values must be integers'])

    def test_apiv2_results_list_filter_combined(self):
        param = {
            "result_type": self.result_type.name,
            "year": datetime.date.today().year,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/reports/results/',
            user=self.unicef_staff,
            data=param,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)
