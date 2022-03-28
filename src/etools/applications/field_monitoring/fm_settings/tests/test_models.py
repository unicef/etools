from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory, LogIssueFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory


class SitesTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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
        cls.country = LocationFactory(admin_level=0)
        cls.boundary_location = LocationFactory(geom=cls.boundary)

    def test_parent_boundary(self):
        site = LocationSiteFactory(parent=None, point=self.boundary_point)
        self.assertEqual(site.parent, self.boundary_location)

    def test_parent_non_boundary(self):
        site = LocationSiteFactory(parent=None, point=self.non_boundary_point)
        self.assertEqual(site.parent, self.country)

    def test_parent_changed(self):
        site = LocationSiteFactory(parent=None, point=self.non_boundary_point)
        self.assertEqual(site.parent, self.country)

        site.point = self.boundary_point
        site.save()

        self.assertEqual(site.parent, self.boundary_location)


class LogIssueTestCase(BaseTenantTestCase):
    def test_multiple_related_objects(self):
        with self.assertRaises(ValidationError):
            LogIssueFactory(
                cp_output=ResultFactory(result_type__name=ResultType.OUTPUT),
                location=LocationFactory()
            )

    def test_related_object_missing(self):
        with self.assertRaises(ValidationError):
            LogIssueFactory()

    def test_related_object_provided(self):
        LogIssueFactory(location=LocationFactory())
