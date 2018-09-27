from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.libraries.tests.api_checker import ViewSetChecker
from unicef_locations.tests.factories import LocationFactory, GatewayTypeFactory, CartoDBTableFactory


class TestAPILocations(BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse("locations-light-list"),
        reverse("locationtypes-list"),
        reverse("locations-list"),
        reverse("locations-detail", args=[101]),
        reverse("locationtypes-list"),
        reverse("locations_detail_pcode", args=['abc']),
        reverse("locations:locations_autocomplete"),
    ]

    def get_fixtures(cls):
        return {'location': LocationFactory(id=101, p_code='abc'),
                'locationtype': GatewayTypeFactory(),
                }


class TestAPICartoDB(BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse("locations:cartodbtables"),
    ]

    def get_fixtures(cls):
        return {'locationtype': CartoDBTableFactory()}
