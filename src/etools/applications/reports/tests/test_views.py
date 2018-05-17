import datetime
from operator import itemgetter

from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.utils import six

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import InterventionFactory, InterventionResultLinkFactory
from etools.applications.partners.tests.test_utils import setup_intervention_test_data
from etools.applications.reports.models import (CountryProgramme, Disaggregation, DisaggregationValue,
                                                LowerResult, ResultType, SpecialReportingRequirement,)
from etools.applications.reports.serializers.v2 import DisaggregationSerializer
from etools.applications.reports.tests.factories import (AppliedIndicatorFactory, CountryProgrammeFactory,
                                                         DisaggregationFactory, DisaggregationValueFactory,
                                                         IndicatorBlueprintFactory, IndicatorFactory,
                                                         LowerResultFactory, ResultFactory, ResultTypeFactory,
                                                         SpecialReportingRequirementFactory,)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class UrlsTestCase(URLAssertionMixin, SimpleTestCase):
    '''Simple test case to verify URL reversal'''

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('reports:applied-indicator', 'applied-indicators/', {}),
            ('reports:country-programme-list', 'countryprogramme/', {}),
            ('reports:lower-results', 'lower_results/', {}),
            ('reports:report-result-list', 'results/', {}),
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
        cls.v2_results_url = reverse('reports:report-result-list')

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
        cls.url = reverse('reports:report-result-list')

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
        first_response = sorted(response.data, key=itemgetter("id"))[0]
        keys = sorted(first_response.keys())
        six.assertCountEqual(self, keys, ['id', 'name'])

    def test_current_cp(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            int(sorted(response.data, key=itemgetter("id"))[0]["country_programme"]),
            CountryProgramme.objects.all_active.first().id)

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
        response_ids = [int(item['id']) for item in response.data]
        result_ids = [self.result1.id, self.result2.id]
        self.assertEqual(sorted(response_ids), sorted(result_ids))

    def test_dropdown(self):
        data = {"dropdown": "true"}
        response = self.forced_auth_req('get', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        six.assertCountEqual(
            self,
            response.data, [
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
            ]
        )


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
        cls.url = reverse('reports:report-result-detail', args=[cls.result1.pk])

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
        cls.pme_user = UserFactory()
        cls.group = GroupFactory(name="PME")
        cls.pme_user.groups.add(cls.group)
        cls.url = reverse('reports:disaggregation-list-create')

    def test_get(self):
        """
        GET returns a list of Disaggregations.
        """
        num_instances = 3
        DisaggregationFactory.create_batch(size=num_instances)
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), num_instances)

    def test_post_non_pme_user(self):
        data = {
            'name': 'Gender',
            'disaggregation_values': [
                {'value': 'Female'},
                {'value': 'Male'},
                {'value': 'Other'},
            ]
        }
        response = self.forced_auth_req('post', self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        response = self.forced_auth_req(
            'post',
            self.url,
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'post',
            self.url,
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestDisaggregationRetrieveUpdateViews(BaseTenantTestCase):
    """
    Very minimal testing, just to make sure things work.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.pme_user = UserFactory()
        cls.group = GroupFactory(name="PME")
        cls.pme_user.groups.add(cls.group)

    @staticmethod
    def _get_url(dissagregation):
        return reverse('reports:disaggregation-retrieve-update', args=[dissagregation.pk])

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

    def test_update_non_pme_user(self):
        disaggregation = DisaggregationFactory()
        new_name = 'updated via API'
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            data={'name': new_name, 'disaggregation_values': []}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_metadata(self):
        """
        Test updating a disaggregation's metadata
        """
        disaggregation = DisaggregationFactory()
        new_name = 'updated via API'
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data={'name': new_name, 'disaggregation_values': []}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        disaggregation = Disaggregation.objects.get(pk=disaggregation.pk)
        self.assertEqual(new_name, disaggregation.name)

    def test_patch_non_pme_user(self):
        disaggregation = DisaggregationFactory()
        new_name = 'patched via API'
        response = self.forced_auth_req(
            'patch',
            self._get_url(disaggregation),
            data={'name': new_name})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_metadata(self):
        """
        Test patching a disaggregation's metadata
        """
        disaggregation = DisaggregationFactory()
        new_name = 'patched via API'
        response = self.forced_auth_req(
            'patch',
            self._get_url(disaggregation),
            user=self.pme_user,
            data={'name': new_name}
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(self.disaggregation),
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # also try with patch
        response = self.forced_auth_req(
            'patch',
            self._get_url(self.disaggregation),
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
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
        response = self.forced_auth_req(
            'put',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # also try with patch
        response = self.forced_auth_req(
            'patch',
            self._get_url(disaggregation),
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete(self):
        """
        Test deleting a disaggregation is not allowed
        """
        disaggregation = DisaggregationFactory()
        response = self.forced_auth_req(
            'delete',
            self._get_url(disaggregation),
            user=self.pme_user
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Disaggregation.objects.filter(pk=disaggregation.pk).exists())


class TestResultIndicatorListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.result = ResultFactory()
        cls.indicator = IndicatorFactory(result=cls.result)
        cls.url = reverse("reports:result-indicator-list", args=[cls.result.pk])

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
            reverse("reports:result-indicator-list", args=[404]),
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([int(x["id"]) for x in response.data], [])


class TestLowerResultListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("reports:lower-results")
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
        self.url = reverse("reports:lower-results-del", args=[self.lower_result.pk])

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
            reverse("reports:lower-results-del", args=[404]),
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
            reverse('reports:lower-results'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('reports:lower-results'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 6)
        self.assertEqual(len(dataset[0]), 6)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('reports:lower-results'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
        cls.url = reverse("reports:applied-indicator")

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
            reverse('reports:applied-indicator'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('reports:applied-indicator'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 26)
        self.assertEqual(len(dataset[0]), 26)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('reports:applied-indicator'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 26)
        self.assertEqual(len(dataset[0]), 26)


class TestSpecialReportingRequirementListCreateView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        group = GroupFactory(name='Partnership Manager')
        cls.unicef_staff.groups.add(group)
        cls.intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.DRAFT,
            in_amendment=True,
        )
        cls.url = reverse(
            "reports:interventions-special-reporting-requirements"
        )

    def test_get(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Current",
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], requirement.pk)
        self.assertEqual(data["intervention"], self.intervention.pk)
        self.assertEqual(data["due_date"], str(requirement.due_date))
        self.assertEqual(data["description"], "Current")

    def test_post(self):
        requirement_qs = SpecialReportingRequirement.objects.filter(
            intervention=self.intervention,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "intervention": self.intervention.pk,
                "due_date": datetime.date(2001, 4, 15),
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        self.assertEqual(response.data["intervention"], self.intervention.pk)
        self.assertEqual(response.data["description"], "Randomness")


class TestSpecialReportingRequirementRetrieveUpdateDestroyView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        group = GroupFactory(name='Partnership Manager')
        cls.unicef_staff.groups.add(group)
        cls.intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.DRAFT,
            in_amendment=True,
        )

    def _get_url(self, requirement):
        return reverse(
            "reports:interventions-special-reporting-requirements-update",
            args=[requirement.pk]
        )

    def test_get(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Current",
        )
        response = self.forced_auth_req(
            "get",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], requirement.pk)
        self.assertEqual(response.data["intervention"], self.intervention.pk)
        self.assertEqual(response.data["due_date"], str(requirement.due_date))
        self.assertEqual(response.data["description"], "Current")

    def test_patch(self):
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "patch",
            self._get_url(requirement),
            user=self.unicef_staff,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "New"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "New")
        requirement_update = SpecialReportingRequirement.objects.get(
            pk=requirement.pk
        )
        self.assertEqual(requirement_update.description, "New")

    def test_delete_invalid_old(self):
        """Cannot delete special reporting requirements in the past"""
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Cannot delete special reporting requirements in the past."]
        )
        self.assertTrue(SpecialReportingRequirement.objects.filter(
            pk=requirement.pk
        ).exists())

    def test_delete(self):
        date = datetime.date.today() + datetime.timedelta(days=10)
        requirement = SpecialReportingRequirementFactory(
            intervention=self.intervention,
            due_date=date,
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SpecialReportingRequirement.objects.filter(
            pk=requirement.pk
        ).exists())
