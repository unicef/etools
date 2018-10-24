from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError

from factory import fuzzy

from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.settings.models import MethodType
from etools.applications.field_monitoring.settings.tests.factories import MethodFactory, LocationSiteFactory


class MethodTypeTestCase(BaseTenantTestCase):
    def test_types_non_applicable(self):
        method = MethodFactory(is_types_applicable=False)

        with self.assertRaises(ValidationError):
            MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()

    def test_types_applicable(self):
        method = MethodFactory(is_types_applicable=True)
        MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()


class SitesTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.boundary = GEOSGeometry(
            """
              {
                "type": "MultiPolygon",
                "coordinates": [
                  [
                    [
                      [
                        83.04496765136719,
                        28.26492642410344
                      ],
                      [
                        83.06024551391602,
                        28.247915770531225
                      ],
                      [
                        83.07638168334961,
                        28.265455600896665
                      ],
                      [
                        83.04496765136719,
                        28.26492642410344
                      ]
                    ]
                  ]
                ]
              }
            """
        )
        cls.boundary_point = GEOSGeometry(
            """
              {
                "type": "Point",
                "coordinates": [
                  83.06058883666992,
                  28.258424894768147
                ]
              }
            """
        )
        cls.non_boundary_point = GEOSGeometry(
            """
              {
                "type": "Point",
                "coordinates": [
                  83.06084632873535,
                  28.26976451410629
                ]
              }
            """
        )
        cls.country = LocationFactory(gateway__admin_level=0)
        cls.boundary_location = LocationFactory(geom=cls.boundary)

    def test_parent_boundary(self):
        site = LocationSiteFactory(parent=None, point=self.boundary_point)
        self.assertEqual(site.parent, self.boundary_location)

    def test_parent_non_boundary(self):
        site = LocationSiteFactory(parent=None, point=self.non_boundary_point)
        self.assertEqual(site.parent, self.country)
