import datetime

from unittest import TestCase

from django.core.urlresolvers import reverse
from rest_framework import status
from partners.tests.test_utils import setup_intervention_test_data
from tablib.core import Dataset

from reports.models import ResultType, CountryProgramme, Disaggregation, DisaggregationValue
from EquiTrack.factories import (
    AppliedIndicatorFactory,
    IndicatorBlueprintFactory,
    InterventionResultLinkFactory,
    LowerResultFactory,
    UserFactory,
    ResultFactory,
    CountryProgrammeFactory,
    DisaggregationFactory,
    DisaggregationValueFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from reports.serializers.v2 import DisaggregationSerializer


class TestReportViews(APITenantTestCase):
    fixtures = ['initial_data.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)  # UNICEF staff user
        cls.result_type = ResultType.objects.get(name=ResultType.OUTPUT)

        today = datetime.date.today()
        cls.country_programme = CountryProgrammeFactory(
            wbs='0000/A0/01',
            from_date=datetime.date(today.year - 1, 1, 1),
            to_date=datetime.date(today.year + 1, 1, 1))

        cls.result1 = ResultFactory(
            result_type=cls.result_type,
            country_programme=cls.country_programme,
        )

        cls.result2 = ResultFactory(
            result_type=cls.result_type,
            country_programme=cls.country_programme
        )
        cls.v2_results_url = reverse('report-result-list')

    def test_api_resulttypes_list(self):
        url = reverse('resulttypes-list')
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_sectors_list(self):
        url = reverse('sectors-list')
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_indicators_list(self):
        url = reverse('indicators-list')
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_results_list(self):
        url = reverse('results-list')
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_api_results_patch(self):
        url = reverse('results-detail', args=[self.result1.id])
        data = {"name": "patched name"}
        response = self.forced_auth_req('patch', url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "patched name")

    def test_api_units_list(self):
        url = reverse('units-list')
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # V2 URLs
    def test_apiv2_results_list(self):
        response = self.forced_auth_req('get', self.v2_results_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_minimal(self):
        data = {"verbosity": "minimal"}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "name"])

    def test_apiv2_results_retrieve(self):
        detail_url = reverse('report-result-detail', args=[self.result1.id])
        response = self.forced_auth_req('get', detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data["id"]), self.result1.id)

    def test_apiv2_results_list_current_cp(self):
        response = self.forced_auth_req('get', self.v2_results_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["country_programme"]), CountryProgramme.objects.all_active.first().id)

    def test_apiv2_results_list_filter_year(self):
        data = {"year": datetime.date.today().year}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_apiv2_results_list_filter_cp(self):
        data = {"country_programme": self.result1.country_programme.id}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_filter_result_type(self):
        data = {"result_type": self.result_type.name}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["id"]), self.result1.id)

    def test_apiv2_results_list_filter_values(self):
        data = {"values": '{},{}'.format(self.result1.id, self.result2.id)}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_apiv2_results_list_filter_values_bad(self):
        data = {"values": '{},{}'.format('23fg', 'aasd67')}
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['ID values must be integers'])

    def test_apiv2_results_list_filter_combined(self):
        data = {
            "result_type": self.result_type.name,
            "year": datetime.date.today().year,
        }
        response = self.forced_auth_req('get', self.v2_results_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.result1.id, [int(i["id"]) for i in response.data])


class TestDisaggregationListCreateViews(APITenantTestCase):
    """
    Very minimal testing, just to make sure things work.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.url = reverse('disaggregation-list-create')

    def test_get(self):
        """
        GET returns a list of Disaggregations.
        """
        num_instances = 3
        DisaggregationFactory.create_batch(size=num_instances)
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), num_instances)

    def test_post(self):
        """
        POST creates a Disaggregation, with DisaggregationValues.
        """
        data = {
            'name': 'Gender',
            'disaggregation_values': [
                {'value': 'Female'},
                {'value': 'Male'},
                {'value': 'Other'},
            ]
        }
        response = self.forced_auth_req('post', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        disaggregation = Disaggregation.objects.get()
        self.assertEqual(disaggregation.name, 'Gender')
        self.assertEqual(disaggregation.disaggregation_values.count(), 3)

    def test_create_disallows_value_ids(self):
        data = {
            'name': 'Gender',
            'disaggregation_values': [
                {'id': 999, 'value': 'Female'},
            ]
        }
        response = self.forced_auth_req('post', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestDisaggregationRetrieveUpdateViews(APITenantTestCase):
    """
    Very minimal testing, just to make sure things work.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)

    @staticmethod
    def _get_url(dissagregation):
        return reverse('disaggregation-retrieve-update', args=[dissagregation.pk])

    def test_get(self):
        """
        Test retrieving a single disaggregation
        """
        disaggregation = DisaggregationFactory()
        num_values = 3
        for i in range(num_values):
            DisaggregationValueFactory(disaggregation=disaggregation)
        response = self.forced_auth_req('get', self._get_url(disaggregation))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(disaggregation.name, response.data['name'])
        self.assertEqual(num_values, len(response.data['disaggregation_values']))

    def test_update_metadata(self):
        """
        Test updating a disaggregation's metadata
        """
        disaggregation = DisaggregationFactory()
        new_name = 'updated via API'
        response = self.forced_auth_req('put', self._get_url(disaggregation),
                                        data={'name': new_name, 'disaggregation_values': []})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(new_name, disaggregation.name)

    def test_patch_metadata(self):
        """
        Test patching a disaggregation's metadata
        """
        disaggregation = DisaggregationFactory()
        new_name = 'patched via API'
        response = self.forced_auth_req('patch', self._get_url(disaggregation),
                                        data={'name': new_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(new_name, disaggregation.name)

    def test_update_values(self):
        """
        Test updating a disaggregation's values
        """
        disaggregation = DisaggregationFactory()
        value = DisaggregationValueFactory(disaggregation=disaggregation)
        new_value = 'updated value'
        data = DisaggregationSerializer(instance=disaggregation).data
        data['disaggregation_values'][0]['value'] = new_value
        response = self.forced_auth_req('put', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(1, disaggregation.disaggregation_values.count())
        updated_value = disaggregation.disaggregation_values.all()[0]
        self.assertEqual(value.pk, updated_value.pk)
        self.assertEqual(new_value, updated_value.value)

    def test_disallow_modifying_referenced_disaggregations(self):
        # this bootstraps a bunch of stuff, including self.disaggregation referenced by an AppliedIndicator
        setup_intervention_test_data(self, include_results_and_indicators=True)
        data = DisaggregationSerializer(instance=self.disaggregation).data
        response = self.forced_auth_req('put', self._get_url(self.disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # also try with patch
        response = self.forced_auth_req('patch', self._get_url(self.disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_values(self):
        """
        Test creating new disaggregation values
        """
        disaggregation = DisaggregationFactory()
        value = DisaggregationValueFactory(disaggregation=disaggregation)
        data = DisaggregationSerializer(instance=disaggregation).data
        data['disaggregation_values'].append({
            "value": "a new value",
            "active": False
        })
        response = self.forced_auth_req('put', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(2, disaggregation.disaggregation_values.count())
        new_value = disaggregation.disaggregation_values.exclude(pk=value.pk)[0]
        self.assertEqual('a new value', new_value.value)

    def test_removing_disaggregation_deletes_it(self):
        disaggregation = DisaggregationFactory()
        value = DisaggregationValueFactory(disaggregation=disaggregation)
        data = DisaggregationSerializer(instance=disaggregation).data
        data['disaggregation_values'] = []
        response = self.forced_auth_req('put', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(0, disaggregation.disaggregation_values.count())
        self.assertFalse(DisaggregationValue.objects.filter(pk=value.pk).exists())

    def test_create_update_delete_value_single_call(self):
        """
        Just test that creation/update/deletion all play nice together.
        """
        disaggregation = DisaggregationFactory()
        v1 = DisaggregationValueFactory(disaggregation=disaggregation)
        v2 = DisaggregationValueFactory(disaggregation=disaggregation)
        DisaggregationValueFactory(disaggregation=disaggregation)
        data = DisaggregationSerializer(instance=disaggregation).data
        # modify the first one
        data['disaggregation_values'][0]['value'] = 'updated'
        # remove the second one
        data['disaggregation_values'] = data['disaggregation_values'][:1]
        # add a new one
        data['disaggregation_values'].append({
            "value": "a new value",
            "active": False
        })
        response = self.forced_auth_req('put', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(2, disaggregation.disaggregation_values.count())
        self.assertEqual('updated', disaggregation.disaggregation_values.get(pk=v1.pk).value)
        self.assertFalse(disaggregation.disaggregation_values.filter(pk=v2.pk).exists())
        self.assertEqual('a new value', disaggregation.disaggregation_values.exclude(pk=v1.pk)[0].value)

    def test_disallow_modifying_unrelated_disaggregation_values(self):
        disaggregation = DisaggregationFactory()
        value = DisaggregationValueFactory()
        data = DisaggregationSerializer(instance=disaggregation).data
        data['disaggregation_values'].append({
            "id": value.pk,
            "value": "not allowed",
        })
        response = self.forced_auth_req('put', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # also try with patch
        response = self.forced_auth_req('patch', self._get_url(disaggregation), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete(self):
        """
        Test deleting a disaggregation is not allowed
        """
        disaggregation = DisaggregationFactory()
        response = self.forced_auth_req('delete', self._get_url(disaggregation))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Disaggregation.objects.filter(pk=disaggregation.pk).exists())


class UrlsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('applied-indicator', 'applied-indicators/', {}),
            ('lower-results', 'lower_results/', {}),
        )
        self.assertReversal(names_and_paths, '', '/api/v2/reports/')


class TestLowerResultExportList(APITenantTestCase):
    def setUp(self):
        super(TestLowerResultExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.result_link = InterventionResultLinkFactory()
        self.lower_result = LowerResultFactory(
            result_link=self.result_link
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('lower-results'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('lower-results'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 6)
        self.assertEqual(len(dataset[0]), 6)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('lower-results'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 6)
        self.assertEqual(len(dataset[0]), 6)


class TestAppliedIndicatorExportList(APITenantTestCase):
    def setUp(self):
        super(TestAppliedIndicatorExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.result_link = InterventionResultLinkFactory()
        self.lower_result = LowerResultFactory(
            result_link=self.result_link
        )
        self.indicator = IndicatorBlueprintFactory()
        self.applied = AppliedIndicatorFactory(
            indicator=self.indicator,
            lower_result=self.lower_result
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('applied-indicator'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('applied-indicator'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 24)
        self.assertEqual(len(dataset[0]), 24)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('applied-indicator'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 24)
        self.assertEqual(len(dataset[0]), 24)
