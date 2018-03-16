import datetime

from unittest import TestCase

from django.core.urlresolvers import reverse
from django.utils import six
from rest_framework import status
from partners.tests.test_utils import setup_intervention_test_data
from tablib.core import Dataset

from EquiTrack.tests.cases import BaseTenantTestCase
from EquiTrack.tests.mixins import URLAssertionMixin
from partners.models import Intervention
from partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
)
from reports.models import (
    CountryProgramme,
    Disaggregation,
    DisaggregationValue,
    LowerResult,
    ResultType,
)
from reports.serializers.v2 import DisaggregationSerializer
from reports.tests.factories import (
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    DisaggregationFactory,
    DisaggregationValueFactory,
    IndicatorBlueprintFactory,
    IndicatorFactory,
    LowerResultFactory,
    ResultFactory,
    ResultTypeFactory,
)
from users.tests.factories import UserFactory


class UrlsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('applied-indicator', 'applied-indicators/', {}),
            ('country-programme-list', 'countryprogramme/', {}),
            ('lower-results', 'lower_results/', {}),
            ('report-result-list', 'results/', {}),
        )
        self.assertReversal(names_and_paths, '', '/api/v2/reports/')


class TestReportViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        for name, _ in ResultType.NAME_CHOICES:
            ResultTypeFactory(name=name)
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
        six.assertCountEqual(
            self,
            [int(r["id"]) for r in response.data],
            [self.result1.pk, self.result2.pk]
        )

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


class TestOutputListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)  # UNICEF staff user
        cls.result_type = ResultTypeFactory(name=ResultType.OUTPUT)

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
        cls.url = reverse('report-result-list')

    def test_get(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        six.assertCountEqual(
            self,
            [int(r["id"]) for r in response.data],
            [self.result1.pk, self.result2.pk]
        )

    def test_minimal(self):
        data = {"verbosity": "minimal"}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "name"])

    def test_current_cp(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data[0]["country_programme"]), CountryProgramme.objects.all_active.first().id)

    def test_filter_year(self):
        data = {"year": datetime.date.today().year}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_cp(self):
        data = {"country_programme": self.result1.country_programme.id}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        six.assertCountEqual(
            self,
            [int(r["id"]) for r in response.data],
            [self.result1.pk, self.result2.pk]
        )

    def test_filter_result_type(self):
        data = {"result_type": self.result_type.name}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        six.assertCountEqual(
            self,
            [int(r["id"]) for r in response.data],
            [self.result1.pk, self.result2.pk]
        )

    def test_filter_values(self):
        data = {"values": '{},{}'.format(self.result1.id, self.result2.id)}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_values_bad(self):
        data = {"values": '{},{}'.format('23fg', 'aasd67')}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['ID values must be integers'])

    def test_filter_combined(self):
        data = {
            "result_type": self.result_type.name,
            "year": datetime.date.today().year,
        }
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.result1.id, [int(i["id"]) for i in response.data])

    def test_dropdown(self):
        data = {"dropdown": "true"}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data, [
            {
                "wbs": self.result1.wbs,
                "id": self.result1.pk,
                "name": self.result1.name
            },
            {
                "wbs": self.result2.wbs,
                "id": self.result2.pk,
                "name": self.result2.name
            },
        ])


class TestOutputDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)  # UNICEF staff user
        cls.result_type = ResultTypeFactory(name=ResultType.OUTPUT)

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
        cls.url = reverse('report-result-detail', args=[cls.result1.pk])

    def test_results_retrieve(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(response.data["id"]), self.result1.id)


class TestDisaggregationListCreateViews(BaseTenantTestCase):
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


class TestDisaggregationRetrieveUpdateViews(BaseTenantTestCase):
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


class TestResultIndicatorListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.result = ResultFactory()
        cls.indicator = IndicatorFactory(result=cls.result)
        cls.url = reverse("result-indicator-list", args=[cls.result.pk])

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [int(x["id"]) for x in response.data],
            [self.indicator.pk]
        )

    def test_get_empty(self):
        response = self.forced_auth_req(
            "get",
            reverse("result-indicator-list", args=[404]),
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([int(x["id"]) for x in response.data], [])


class TestLowerResultListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("lower-results")
        cls.intervention = InterventionFactory()
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention,
        )
        cls.lower_result = LowerResultFactory(
            name="LL Name",
            result_link=cls.result_link,
        )

    def test_search_number(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:4]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            self.lower_result.pk,
            [int(x["id"]) for x in response.data]
         )

    def test_search_name(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": "LL Name"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            self.lower_result.pk,
            [int(x["id"]) for x in response.data]
         )

    def test_search_empty(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": "wrong"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class TestLowerResultDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory()
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention,
        )

    def setUp(self):
        self.lower_result = LowerResultFactory(
            result_link=self.result_link,
        )
        self.url = reverse("lower-results-del", args=[self.lower_result.pk])

    def test_delete(self):
        self.intervention.unicef_focal_points.add(self.unicef_staff)
        response = self.forced_auth_req(
            "delete",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            LowerResult.objects.filter(pk=self.lower_result.pk).exists()
        )

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            "delete",
            reverse("lower-results-del", args=[404]),
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            LowerResult.objects.filter(pk=self.lower_result.pk).exists()
        )

    def test_delete_bad_request(self):
        """If user does not have permissions, expect 400 response"""
        user = UserFactory()
        self.intervention.status = Intervention.ENDED
        self.intervention.save()
        response = self.forced_auth_req(
            "delete",
            self.url,
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            LowerResult.objects.filter(pk=self.lower_result.pk).exists()
        )


class TestLowerResultExportList(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(
            result_link=cls.result_link
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


class TestAppliedIndicatorListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory()
        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(
            name="LL Name",
            result_link=cls.result_link,
        )
        cls.indicator = IndicatorBlueprintFactory()
        cls.applied = AppliedIndicatorFactory(
            context_code="CC321",
            indicator=cls.indicator,
            lower_result=cls.lower_result
        )
        cls.url = reverse("applied-indicator")

    def test_search_number(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:4]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [int(x["id"]) for x in response.data],
            [self.applied.pk]
        )

    def test_search_name(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": "LL Name"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [int(x["id"]) for x in response.data],
            [self.applied.pk]
        )

    def test_search_context_code(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": "CC321"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [int(x["id"]) for x in response.data],
            [self.applied.pk]
        )

    def test_search_empty(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"search": "wrong"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class TestAppliedIndicatorExportList(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(
            result_link=cls.result_link
        )
        cls.indicator = IndicatorBlueprintFactory()
        cls.applied = AppliedIndicatorFactory(
            indicator=cls.indicator,
            lower_result=cls.lower_result
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
