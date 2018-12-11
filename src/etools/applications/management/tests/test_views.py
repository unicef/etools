from django.urls import reverse

from django_tenants.test.client import TenantClient
from mock import patch
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.activities.models import Activity
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, UserFactory


class InvalidateCacheTest(BaseTenantTestCase):

    def setUp(self):
        self.staff_user = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_superuser=True)
        self.url = reverse('management:invalidate_cache')

    def test_not_superuser(self):
        """
        Only superusers are allowed to use this view.
        """
        response = self.forced_auth_req('get', self.url, user=self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_key(self):
        """
        If key is not provided, return an error message.
        """
        response = self.forced_auth_req('get', self.url, user=self.superuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must pass "key" as a query param')

    @patch('etools.applications.management.views.general.cache')
    def test_valid_key(self, mock_cache):
        """
        If key is provided, return 200 success message and call cache API to delete key.
        """
        cache_key_to_delete = 'delete-me'
        request_data = {
            'key': cache_key_to_delete,
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], 'key removed if it was present')
        # assert that cache.delete() was called properly
        mock_cache.delete.assert_called_with(cache_key_to_delete)


class LoadResultStructureTest(BaseTenantTestCase):

    def setUp(self):
        self.staff_user = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_superuser=True)
        self.url = reverse('management:load_result_structure')

    def test_not_superuser(self):
        """
        Only superusers are allowed to use this view.
        """
        response = self.forced_auth_req('get', self.url, user=self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_country(self):
        """
        Return 400 if no country supplied.
        """
        response = self.forced_auth_req('get', self.url, user=self.superuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Country not found')

    def test_bad_country(self):
        """
        Return 400 if country not found in our database.
        """
        request_data = {
            'country': 'Bad Country',
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Country not found')

    @patch('etools.applications.management.views.reports.ProgrammeSynchronizer')
    def test_good_country(self, mock_synchronizer):
        """
        Sync country and return success response.
        """
        country = CountryFactory()
        request_data = {
            'country': country.name,
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], 'Country = {}'.format(country.name))
        # assert that sync was called
        mock_synchronizer.return_value.sync.assert_called()

    @patch('etools.applications.management.views.reports.ProgrammeSynchronizer')
    def test_good_country_sync_error(self, mock_synchronizer):
        """
        If Synchronizer throws an error, then return 500.
        """
        country = CountryFactory()
        request_data = {
            'country': country.name,
        }
        mock_synchronizer.return_value.sync.side_effect = Exception
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestActiveUser(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            reverse("management:stats_user_counts"),
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{
            "countryName": "",
            "records": {"total": 1}
        }])


class TestAgreementsStatisticsView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            reverse("management:stats_agreements"),
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{
            "countryName": "",
            "totalAgreements": 0
        }])


class TestPortalDashView(BaseTenantTestCase):
    def test_get(self):
        self.client = TenantClient(self.tenant)
        response = self.client.get(reverse("management:dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestGisLocationViews(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.unicef_staff = UserFactory(is_superuser=True)
        group = GroupFactory()
        self.unicef_staff.groups.add(group)
        self.country = CountryFactory()
        self.unicef_staff.profile.country = self.country
        self.unicef_staff.save()
        self.partner = PartnerFactory()
        self.agreement = AgreementFactory(partner=self.partner)
        self.intervention = InterventionFactory(agreement=self.agreement)
        self.location_no_geom = LocationFactory(name="Test no geom")
        self.location_with_geom = LocationFactory(
            name="Test with geom",
            geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))"
        )
        self.inactive_location = LocationFactory(is_active=False)
        self.locations = [self.location_no_geom, self.location_with_geom]

    def assertGeomListResponseFundamentals(self, response, response_len, expected_keys=None):
        '''
        Assert common fundamentals about the response.
        '''
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        if not expected_keys:
            expected_keys = ["features", "type"]
        self.assertEqual(sorted(response.data.keys()), expected_keys)

        # see if the response is a valid GeoJson
        self.assertEqual(response.data["type"], "FeatureCollection")
        self.assertEqual(len(response.data['features']), response_len)

        if len(response.data['features']) > 0:
            for feature in response.data['features']:
                self.assertKeysIn(['id', 'type', 'geometry', 'properties'], feature)

    def test_no_permission(self):
        response = self.forced_auth_req('get', reverse("management_gis:locations-gis-geom-list"), user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req('get', reverse("management_gis:locations-gis-in-use"), user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_geoformat(self):
        url = reverse("management_gis:locations-gis-geom-list")

        response = self.forced_auth_req(
            "get",
            url,  # geo_format should be either geojson or wkt
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "whatever"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        url = reverse("management_gis:locations-gis-get-by-pcode", kwargs={"pcode": self.location_with_geom.p_code})
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        url = reverse("management_gis:locations-gis-get-by-id", kwargs={"id": self.location_with_geom.id})
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_locations_in_use(self):
        url = reverse("management_gis:locations-gis-in-use")

        # test with missing country, expect error
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.forced_auth_req(
            "get",
            reverse("management_gis:locations-gis-in-use"),
            user=self.unicef_staff,
            data={"country_id": self.country.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # see if no location are in use yet
        self.assertEqual(len(response.data), 0)

    def test_travel_locations_in_use(self):
        travel = TravelFactory(
            traveler=self.unicef_staff,
            status=Travel.COMPLETED,
        )
        travel_activity = TravelActivityFactory(
            travels=[travel],
            primary_traveler=self.unicef_staff,
            travel_type=TravelType.SPOT_CHECK,
        )
        travel_activity.locations.add(self.location_no_geom.id, self.location_with_geom.id)
        travel_activity.save()

        response = self.forced_auth_req(
            "get",
            reverse("management_gis:locations-gis-in-use"),
            user=self.unicef_staff,
            data={"country_id": self.country.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway_id", "id", "level", "name", "p_code", "parent_id"])

    def test_intervention_locations_in_use(self):
        # add intervention locations and test the response
        intervention = InterventionFactory(status=Intervention.SIGNED)
        intervention.flat_locations.add(self.location_no_geom, self.location_with_geom)
        intervention.save()

        response = self.forced_auth_req(
            "get",
            reverse("management_gis:locations-gis-in-use"),
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "whatever"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway_id", "id", "level", "name", "p_code", "parent_id"])

    def test_activities_in_use(self):
        activity = Activity(
            partner=self.partner,
            intervention=self.intervention
        )
        activity.save()
        activity.locations.add(*self.locations)

        response = self.forced_auth_req(
            "get",
            reverse("management_gis:locations-gis-in-use"),
            user=self.unicef_staff,
            data={"country_id": self.country.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway_id", "id", "level", "name", "p_code", "parent_id"])

    def test_action_points_in_use(self):
        ActionPointFactory(
            location=self.location_no_geom
        )

        response = self.forced_auth_req(
            "get",
            reverse("management_gis:locations-gis-in-use"),
            user=self.unicef_staff,
            data={"country_id": self.country.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway_id", "id", "level", "name", "p_code", "parent_id"])

    def test_intervention_locations_geom_bad_request(self):
        url = reverse("management_gis:locations-gis-geom-list")
        # test with no country in the query string, expect error
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_intervention_locations_geom(self):
        url = reverse("management_gis:locations-gis-geom-list")

        # test with no format filter, we should expect GeoJson in the response
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id},
        )
        # expect all 3(2 active + 1 inactive) locations in the response
        self.assertGeomListResponseFundamentals(response, 3)

    def test_intervention_locations_geom_status_all(self):
        url = reverse("management_gis:locations-gis-geom-list")

        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, 'status': 'all'},
        )
        # expect all 3(2 active + 1 inactive) locations in the response
        self.assertGeomListResponseFundamentals(response, 3)

    def test_intervention_locations_geom_status_active(self):
        url = reverse("management_gis:locations-gis-geom-list")

        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, 'status': 'active'},
        )
        # expect 2 active locations in the response
        self.assertGeomListResponseFundamentals(response, 2)

    def test_intervention_locations_geom_status_archived(self):
        # test with missing country in the query string, expect error
        url = reverse("management_gis:locations-gis-geom-list")
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, 'status': 'archived'},
        )
        # expect 1 archived location in the response
        self.assertGeomListResponseFundamentals(response, 1)

    def test_intervention_locations_geom_geojson(self):
        url = reverse("management_gis:locations-gis-geom-list")

        # test with GEOJSON format
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "geojson", "geom_type": "polygon"},
        )
        # expect 1 active polygon location in the response
        self.assertGeomListResponseFundamentals(response, 1)

    def test_intervention_locations_geom_wkt(self):
        url = reverse("management_gis:locations-gis-geom-list")

        # test with WKT format
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "wkt", "geom_type": "polygon"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # only one of the test locations has GEOM
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            sorted(response.data[0].keys()),
            ["gateway_id", "geom", "id", "level", "name", "p_code", "parent_id", "point"]
        )
        self.assertEqual(response.data[0]["geom"], self.location_with_geom.geom.wkt)

    def test_intervention_locations_geom_by_pcode(self):
        url = reverse("management_gis:locations-gis-get-by-pcode", kwargs={"pcode": self.location_with_geom.p_code})

        # test with missing country, expect error
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # request the result in WKT
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "wkt"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            sorted(response.data.keys()),
            ["gateway_id", "geom", "id", "level", "name", "p_code", "parent_id", "point"]
        )
        self.assertEqual(response.data["id"], str(self.location_with_geom.id))
        self.assertEqual(response.data["geom"], self.location_with_geom.geom.wkt)

        # request the result in GeoJson
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "geojson"},
        )
        # see if the response is a valid Feature
        self.assertKeysIn(['id', 'type', 'geometry', 'properties'], response.data)
        self.assertEqual(response.data["type"], "Feature")
        self.assertEqual(response.data["geometry"]['type'], 'MultiPolygon')
        # TODO: check returned coordinates, and add 1 more test with POINT() returned
        self.assertIsNotNone(response.data["geometry"]['coordinates'])

    def test_intervention_locations_geom_by_id(self):
        url = reverse("management_gis:locations-gis-get-by-id", kwargs={"id": self.location_with_geom.id})

        # test with missing country, expect error
        response = self.forced_auth_req("get", url, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # request the result in WKT
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "wkt"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            sorted(response.data.keys()),
            ["gateway_id", "geom", "id", "level", "name", "p_code", "parent_id", "point"]
        )
        self.assertEqual(response.data["id"], str(self.location_with_geom.id))
        self.assertEqual(response.data["geom"], self.location_with_geom.geom.wkt)

        # request the result in GeoJson
        response = self.forced_auth_req(
            "get",
            url,
            user=self.unicef_staff,
            data={"country_id": self.country.id, "geo_format": "geojson"},
        )
        # see if the response is a valid Feature
        self.assertKeysIn(['id', 'type', 'geometry', 'properties'], response.data)
        self.assertEqual(response.data["type"], "Feature")
        self.assertEqual(response.data["geometry"]['type'], 'MultiPolygon')
        # TODO: check returned coordinates, and add 1 more test with POINT() returned
        self.assertIsNotNone(response.data["geometry"]['coordinates'])
