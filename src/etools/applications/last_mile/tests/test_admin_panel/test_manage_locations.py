from unittest.mock import patch

from django.contrib.gis.geos import GEOSGeometry

from rest_framework import status
from rest_framework.reverse import reverse
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import PointOfInterestFactory, PointOfInterestTypeFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserPermissionFactory


class TestLocationsViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name="Partner"))
        cls.partner_2 = PartnerFactory(
            organization=OrganizationFactory(name="Partner 2")
        )
        cls.partner_3 = PartnerFactory(
            organization=OrganizationFactory(name="Partner 3")
        )
        cls.partner_4 = PartnerFactory(
            organization=OrganizationFactory(name="Partner 4")
        )
        cls.organization = OrganizationFactory(name="Update Organization")
        cls.partner_staff = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[
                LOCATIONS_ADMIN_PANEL_PERMISSION,
                APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION,
            ],
        )
        cls.partner_staff_without_approve_perms = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.organization,
            perms=[LOCATIONS_ADMIN_PANEL_PERMISSION],
        )
        cls.simple_user = SimpleUserFactory()
        cls.poi_type = PointOfInterestTypeFactory(name="School", category="school")
        cls.poi_type_2 = PointOfInterestTypeFactory(
            name="Hospital", category="hospital"
        )
        cls.poi_type_3 = PointOfInterestTypeFactory(
            name="Warehouse", category="warehouse"
        )
        cls.poi_partner_1 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
        )
        cls.poi_partner_2 = PointOfInterestFactory(
            partner_organizations=[cls.partner_2],
            private=True,
            poi_type_id=cls.poi_type_2.id,
        )
        cls.poi_partner_3 = PointOfInterestFactory(
            partner_organizations=[cls.partner_3],
            private=True,
            poi_type_id=cls.poi_type_3.id,
        )
        cls.poi_partner_4 = PointOfInterestFactory(
            partner_organizations=[cls.partner_4],
            private=True,
            poi_type_id=cls.poi_type_3.id,
        )
        cls.parent_location_1 = LocationFactory(
            name="Somalia",
            admin_level=0,
            geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))",
        )
        cls.parent_location_2 = LocationFactory(
            name="Some Region",
            admin_level=1,
            parent=cls.parent_location_1,
            geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))",
        )
        cls.parent_location_3 = LocationFactory(
            name="Some District",
            admin_level=2,
            parent=cls.parent_location_2,
            geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))",
        )
        cls.poi = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            parent=cls.parent_location_1,
        )
        cls.poi_filter_1 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location A",
            p_code="F001",
            description="Filter Desc A",
            point=GEOSGeometry("POINT(54.21342 25.432432)"),
            parent=cls.parent_location_2,
        )
        cls.poi_filter_2 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location B",
            p_code="F002",
            description="Filter Desc B",
            point=GEOSGeometry("POINT(43.2323 34.123213)"),
            parent=cls.parent_location_3,
        )
        cls.poi_filter_3 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location C",
            p_code="F003",
            description="Filter Desc C",
            point=GEOSGeometry("POINT(43.6532 79.3832)"),
        )
        cls.parent_location = LocationFactory()
        cls.url = reverse(f"{ADMIN_PANEL_APP_NAME}:{LOCATIONS_ADMIN_PANEL}-list")
        cls.url_coordinates = reverse(
            f"{ADMIN_PANEL_APP_NAME}:{GEOPOINT_LOCATIONS}-list"
        )

        cls.review_url = cls.url + "bulk-review/"
        cls.poi_pending_1 = PointOfInterestFactory(
            status=models.PointOfInterest.ApprovalStatus.PENDING,
            partner_organizations=[cls.partner],
        )
        cls.poi_pending_2 = PointOfInterestFactory(
            status=models.PointOfInterest.ApprovalStatus.PENDING,
            partner_organizations=[cls.partner],
        )
        cls.poi_initially_approved = PointOfInterestFactory(
            status=models.PointOfInterest.ApprovalStatus.APPROVED,
            partner_organizations=[cls.partner],
            review_notes="Initial approval.",
        )
        cls.poi_initially_rejected = PointOfInterestFactory(
            status=models.PointOfInterest.ApprovalStatus.REJECTED,
            partner_organizations=[cls.partner],
            review_notes="Initial rejection.",
        )

    def test_get_locations(self):
        response = self.forced_auth_req("get", self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 12)

    def test_get_location_with_coordinates(self):
        data = {"with_coordinates": True}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 12)

    def test_get_locations_with_coordinates_data(self):
        data = {"with_coordinates": True}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 12)
        result = response.data.get("results")
        borders_count = 0
        for location in result:
            borders = location.get("borders", {}).get("country", {}).get("borders")
            if borders:
                self.assertEqual(len(borders), 2)
                borders_count += 1
        self.assertEqual(borders_count, 3)

    def test_get_locations_empty_borders(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        data = {"with_coordinates": True}
        response = self.forced_auth_req(
            "get", url_with_param, user=self.partner_staff, data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        border = response.data.get("borders", {}).get("country", {}).get("borders")
        self.assertEqual(border, [])

    def test_get_specific_location_with_border(self):
        url_with_param = self.url + f"{self.poi_filter_1.pk}/"
        data = {"with_coordinates": True}
        response = self.forced_auth_req(
            "get", url_with_param, user=self.partner_staff, data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        border = response.data.get("borders", {}).get("country", {}).get("borders")
        self.assertEqual(
            border,
            [
                (
                    (
                        (10.0, 10.0),
                        (10.0, 20.0),
                        (20.0, 20.0),
                        (20.0, 15.0),
                        (10.0, 10.0),
                    ),
                ),
                (
                    (
                        (10.0, 10.0),
                        (10.0, 20.0),
                        (20.0, 20.0),
                        (20.0, 15.0),
                        (10.0, 10.0),
                    ),
                ),
            ],
        )

    def test_get_only_coordinates(self):
        response = self.forced_auth_req(
            "get", self.url_coordinates, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 12)

    def test_get_locations_unauthorized(self):
        response = self.forced_auth_req("get", self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_specific_location(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        response = self.forced_auth_req("get", url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("name"), self.poi_partner_1.name)
        self.assertEqual(response.data.get("private"), self.poi_partner_1.private)
        self.assertEqual(response.data.get("poi_type").get("name"), self.poi_type.name)
        self.assertEqual(
            response.data.get("poi_type").get("category"), self.poi_type.category
        )
        self.assertEqual(
            response.data.get("partner_organizations")[0].get("name"), self.partner.name
        )
        self.assertEqual(
            response.data.get("partner_organizations")[0].get("vendor_number"),
            self.partner.vendor_number,
        )
        self.assertEqual(response.data.get("is_active"), self.poi_partner_1.is_active)

    def test_get_specific_locations_unauthorized(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        response = self.forced_auth_req("get", url_with_param, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def get_specific_location_invalid_id(self):
        url_with_param = self.url + "invalid_id/"
        response = self.forced_auth_req("get", url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_location_success(self):
        payload = {
            "name": "New Location",
            "parent": self.parent_location.pk,  # using an existing POI as parent
            "p_code": "P001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "secondary_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("name"), "New Location")

    def test_create_location_missing_required_field(self):
        payload = {
            "parent": self.poi.pk,
            "p_code": "P002",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_parent(self):
        payload = {
            "name": "Invalid Parent",
            "parent": 9999,  # non-existent parent -> Parent is set based on the coordinates
            "p_code": "P003",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_location_invalid_partner_organizations(self):
        payload = {
            "name": "Invalid Partner Org",
            "parent": self.poi.pk,
            "p_code": "P004",
            "partner_organizations": [9999],  # non-existent partner organization
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_poi_type(self):
        payload = {
            "name": "Invalid POI Type",
            "parent": self.poi.pk,
            "p_code": "P005",
            "partner_organizations": [self.partner.pk],
            "poi_type": 9999,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_geometry(self):
        payload = {
            "name": "Invalid Geometry",
            "parent": self.poi.pk,
            "p_code": "P006",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": "invalid"},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_unauthorized(self):
        payload = {
            "name": "Unauthorized Location",
            "parent": self.poi.pk,
            "p_code": "P007",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_location_success(self):
        payload = {"name": "Updated Name"}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req(
            "patch", url_with_param, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("name"), "Updated Name")

    def test_update_location_invalid_poi_type(self):
        payload = {"poi_type": 9999}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req(
            "patch", url_with_param, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_location_invalid_partner_organizations(self):
        payload = {"partner_organizations": [9999]}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req(
            "patch", url_with_param, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_location_unauthorized(self):
        payload = {"name": "Should Not Update"}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req(
            "patch", url_with_param, data=payload, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_nonexistent_numeric_location(self):
        non_existent_id = self.poi.pk + 1000
        url_with_param = self.url + f"{non_existent_id}/"
        response = self.forced_auth_req("get", url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_location_invalid_id_format(self):
        url_with_param = self.url + "invalid_id/"
        response = self.forced_auth_req("get", url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_location_not_allowed(self):
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req(
            "delete", url_with_param, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_export_csv_success(self):
        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req("get", csv_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content_disposition = response.headers.get("Content-Disposition", "")
        self.assertTrue(
            content_disposition.startswith('attachment; filename="locations_')
        )

    def test_export_csv(self):
        response = self.forced_auth_req('get', self.url + "export/csv/", user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Content-Disposition', response.headers)
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('Unique ID', content)
        self.assertIn('Name', content)
        self.assertIn('Primary Type', content)
        self.assertIn('P Code', content)
        self.assertIn('Latitude', content)
        self.assertIn('Longitude', content)
        self.assertIn('Status', content)
        self.assertIn('Implementing Partner', content)
        self.assertIn('Region', content)
        self.assertIn('District', content)
        self.assertIn('Country', content)

    def test_export_csv_unauthorized(self):
        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req("get", csv_url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_p_code(self):
        response = self.forced_auth_req(
            "get", self.url, data={"p_code": "F002"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data.get("results")[0].get("p_code"), "F002")

    def test_filter_by_latitude(self):
        response = self.forced_auth_req(
            "get", self.url, data={"latitude": "79"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)

    def test_filter_by_longitude(self):
        response = self.forced_auth_req(
            "get", self.url, data={"longitude": "43"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 2)

    def test_filter_by_country(self):
        response = self.forced_auth_req(
            "get", self.url, data={"country": "Somalia"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 3)

    def test_filter_by_region(self):
        response = self.forced_auth_req(
            "get", self.url, data={"region": "Some Region"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 2)

    def test_filter_by_district(self):
        response = self.forced_auth_req(
            "get", self.url, data={"district": "Some District"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)

    def test_filter_by_is_active(self):
        response = self.forced_auth_req(
            "get", self.url, data={"is_active": True}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 12)

    def test_filter_by_partner_organization(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            data={"partner_organization": self.partner_2.organization.name},
            user=self.partner_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)

    def test_ordering_by_p_code(self):
        response = self.forced_auth_req(
            "get", self.url, data={"ordering": "p_code"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results")
        p_codes = [r.get("p_code") for r in results]
        self.assertEqual(p_codes, sorted(p_codes))

    def test_list_locations_permission_denied(self):
        response = self.forced_auth_req(
            "get", self.url, data={"country": "CountryA"}, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_location_permission_denied(self):
        url_with_param = self.url + f"{self.poi_filter_1.pk}/"
        response = self.forced_auth_req("get", url_with_param, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_approve_success(self):
        pois_to_approve = [self.poi_pending_1, self.poi_pending_2]
        poi_ids = [p.pk for p in pois_to_approve]
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": poi_ids,
            "review_notes": "All look good.",
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for poi in pois_to_approve:
            poi.refresh_from_db()
            self.assertEqual(poi.status, models.PointOfInterest.ApprovalStatus.APPROVED)
            self.assertEqual(poi.approved_by, self.partner_staff)
            self.assertIsNotNone(poi.approved_on)
            self.assertEqual(poi.review_notes, "All look good.")

    def test_bulk_reject_success(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.REJECTED,
            "points_of_interest": [self.poi_pending_1.pk],
            "review_notes": "Location data is inaccurate.",
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(
            self.poi_pending_1.status, models.PointOfInterest.ApprovalStatus.REJECTED
        )
        self.assertEqual(self.poi_pending_1.approved_by, self.partner_staff)
        self.assertIsNotNone(self.poi_pending_1.approved_on)
        self.assertEqual(
            self.poi_pending_1.review_notes, "Location data is inaccurate."
        )

    def test_bulk_reject_without_notes(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.REJECTED,
            "points_of_interest": [self.poi_pending_1.pk],
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(
            self.poi_pending_1.status, models.PointOfInterest.ApprovalStatus.REJECTED
        )
        self.assertIsNone(self.poi_pending_1.review_notes)

    def test_bulk_review_transition_approved_to_rejected(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.REJECTED,
            "points_of_interest": [self.poi_initially_approved.pk],
            "review_notes": "Re-evaluated and rejected.",
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_initially_approved.refresh_from_db()
        self.assertEqual(
            self.poi_initially_approved.status,
            models.PointOfInterest.ApprovalStatus.REJECTED,
        )
        self.assertEqual(
            self.poi_initially_approved.review_notes, "Re-evaluated and rejected."
        )
        self.assertEqual(self.poi_initially_approved.approved_by, self.partner_staff)

    def test_bulk_review_transition_rejected_to_approved(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_initially_rejected.pk],
            "review_notes": "Corrections were made.",
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_initially_rejected.refresh_from_db()
        self.assertEqual(
            self.poi_initially_rejected.status,
            models.PointOfInterest.ApprovalStatus.APPROVED,
        )
        self.assertEqual(
            self.poi_initially_rejected.review_notes, "Corrections were made."
        )
        self.assertEqual(self.poi_initially_rejected.approved_by, self.partner_staff)

    def test_bulk_review_idempotent_request_updates_fields(self):
        """Test that re-approving an approved POI works and updates the review fields. Should not change anything"""
        original_approved_on = self.poi_initially_approved.approved_on
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_initially_approved.pk],
            "review_notes": "Confirmed approval.",
        }

        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_initially_approved.refresh_from_db()
        self.assertEqual(
            self.poi_initially_approved.status,
            models.PointOfInterest.ApprovalStatus.APPROVED,
        )
        self.assertEqual(self.poi_initially_approved.review_notes, "Initial approval.")
        self.assertEqual(self.poi_initially_approved.approved_on, original_approved_on)

    def test_bulk_review_fails_for_forbidden_status_pending(self):
        """A review endpoint should not allow setting the status back to PENDING."""
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.PENDING,
            "points_of_interest": [self.poi_initially_approved.pk],
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_bulk_review_fails_if_any_poi_id_is_invalid(self):
        """Tests the atomicity of the request; if one POI is invalid, the whole request fails."""
        non_existent_id = 999999
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_pending_1.pk, non_existent_id],
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("points_of_interest", response.data)

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(
            self.poi_pending_1.status, models.PointOfInterest.ApprovalStatus.PENDING
        )

    def test_bulk_review_unauthorized_user(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_pending_1.pk],
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_review_method_not_allowed(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_pending_1.pk],
        }
        response_post = self.forced_auth_req(
            "post", self.review_url, data=payload, user=self.partner_staff
        )
        response_get = self.forced_auth_req(
            "get", self.review_url, user=self.partner_staff
        )
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response_get.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_approve_without_correct_permissions(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_pending_1.pk],
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("etools.applications.last_mile.models.PointOfInterest.approve")
    def test_bulk_review_atomic_transaction_rolls_back_on_failure(self, mock_approve):
        mock_approve.side_effect = [None, Exception("Simulated database error")]

        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [self.poi_pending_1.pk, self.poi_pending_2.pk],
        }

        with self.assertRaises(Exception):
            self.forced_auth_req(
                "put", self.review_url, data=payload, user=self.partner_staff
            )

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(
            self.poi_pending_1.status,
            models.PointOfInterest.ApprovalStatus.PENDING,
            "The first POI's status should have been rolled back",
        )

    def test_create_location_with_special_characters(self):
        payload = {
            "name": "Location @#$%^&*()_+-=[]{}|;:,.<>?",
            "parent": self.parent_location.pk,
            "p_code": "SPEC001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_location_with_maximum_length_fields(self):
        max_length_name = "A" * 254
        max_length_pcode = "P" * 31
        payload = {
            "name": max_length_name,
            "parent": self.parent_location.pk,
            "p_code": max_length_pcode,
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_location_with_exceeding_length_fields(self):
        too_long_name = "A" * 300
        payload = {
            "name": too_long_name,
            "parent": self.parent_location.pk,
            "p_code": "LONG001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_with_empty_string_name(self):
        payload = {
            "name": "",
            "parent": self.parent_location.pk,
            "p_code": "EMPTY001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_with_whitespace_only_name(self):
        payload = {
            "name": "   \t\n   ",
            "parent": self.parent_location.pk,
            "p_code": "WHITE001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_with_extreme_coordinates(self):
        extreme_coordinates = [
            {"type": "Point", "coordinates": [180.0, 90.0]},
            {"type": "Point", "coordinates": [-180.0, -90.0]},
            {"type": "Point", "coordinates": [179.999999, 89.999999]},
        ]

        for i, coords in enumerate(extreme_coordinates):
            payload = {
                "name": f"Extreme Location {i}",
                "parent": self.parent_location.pk,
                "p_code": f"EXT00{i}",
                "partner_organizations": [self.partner.pk],
                "poi_type": self.poi_type.pk,
                "point": coords,
            }
            response = self.forced_auth_req(
                "post", self.url, data=payload, user=self.partner_staff
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Failed for coordinates: {coords}",
            )

    def test_create_location_with_duplicate_pcode(self):
        payload1 = {
            "name": "First Location",
            "parent": self.parent_location.pk,
            "p_code": "DUP001",
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response1 = self.forced_auth_req(
            "post", self.url, data=payload1, user=self.partner_staff
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        payload2 = {
            "name": "Second Location",
            "parent": self.parent_location.pk,
            "p_code": "DUP001",  # Same p_code -> Will be created, because the p_code is set up on the BE
            "partner_organizations": [self.partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [44.7, 26.6]},
        }
        response2 = self.forced_auth_req(
            "post", self.url, data=payload2, user=self.partner_staff
        )
        last_poi = models.PointOfInterest.objects.last()
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(last_poi.p_code, "tes000000002")

    def test_create_location_with_multiple_partner_organizations(self):
        payload = {
            "name": "Multi Partner Location",
            "parent": self.parent_location.pk,
            "p_code": "MULTI001",
            "partner_organizations": [
                self.partner.pk,
                self.partner_2.pk,
                self.partner_3.pk,
            ],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data.get("partner_organizations")), 3)

    def test_filter_by_multiple_pcodes(self):
        response = self.forced_auth_req(
            "get", self.url, data={"p_code": "F001,F002"}, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_nonexistent_country(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            data={"country": "NonExistentCountry123"},
            user=self.partner_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 0)

    def test_filter_with_special_characters_in_search(self):
        search_params = ["@test", "%wildcard", "test*location", 'test"quote']

        for search_term in search_params:
            response = self.forced_auth_req(
                "get", self.url, data={"search": search_term}, user=self.partner_staff
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ordering_with_invalid_field(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            data={"ordering": "nonexistent_field"},
            user=self.partner_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bulk_review_with_duplicate_poi_ids(self):
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.APPROVED,
            "points_of_interest": [
                self.poi_pending_1.pk,
                self.poi_pending_1.pk,
                self.poi_pending_2.pk,
            ],
            "review_notes": "Duplicate IDs test",
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(
            self.poi_pending_1.status, models.PointOfInterest.ApprovalStatus.APPROVED
        )

    def test_bulk_review_with_very_long_review_notes(self):
        long_notes = "A" * 10000
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.REJECTED,
            "points_of_interest": [self.poi_pending_1.pk],
            "review_notes": long_notes,
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK])

    def test_bulk_review_with_unicode_review_notes(self):
        unicode_notes = "تم الرفض بسبب عدم صحة البيانات 测试审批 🚫❌"
        payload = {
            "status": models.PointOfInterest.ApprovalStatus.REJECTED,
            "points_of_interest": [self.poi_pending_1.pk],
            "review_notes": unicode_notes,
        }
        response = self.forced_auth_req(
            "put", self.review_url, data=payload, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poi_pending_1.refresh_from_db()
        self.assertEqual(self.poi_pending_1.review_notes, unicode_notes)

    def test_update_location_with_null_values(self):
        payloads = [{"name": None}, {"description": None}, {"p_code": None}]

        for payload in payloads:
            url_with_param = self.url + f"{self.poi.pk}/"
            response = self.forced_auth_req(
                "patch", url_with_param, data=payload, user=self.partner_staff
            )
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )

    def test_export_csv_with_large_dataset_simulation(self):
        for i in range(50):
            PointOfInterestFactory(
                partner_organizations=[self.partner],
                private=True,
                poi_type_id=self.poi_type.id,
                name=f"Export Test Location {i}",
                p_code=f"EXP{i:03d}",
            )

        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req("get", csv_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response.get("Content-Type", ""))

    def test_location_crud_with_inactive_related_objects(self):
        inactive_partner = PartnerFactory(
            organization=OrganizationFactory(name="Inactive Partner"), hidden=True
        )

        payload = {
            "name": "Location with Inactive Partner",
            "parent": self.parent_location.pk,
            "p_code": "INACTIVE001",
            "partner_organizations": [inactive_partner.pk],
            "poi_type": self.poi_type.pk,
            "point": {"type": "Point", "coordinates": [43.7, 25.6]},
        }
        response = self.forced_auth_req(
            "post", self.url, data=payload, user=self.partner_staff
        )
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

    def test_case_sensitivity_in_filters(self):
        PointOfInterestFactory(
            partner_organizations=[self.partner],
            private=True,
            poi_type_id=self.poi_type.id,
            name="CaseSensitive Location",
            p_code="CASE001",
        )

        case_variations = [
            {"country": "somalia"},
            {"country": "SOMALIA"},
            {"country": "Somalia"},
            {"search": "casesensitive"},
            {"search": "CASESENSITIVE"},
        ]

        for variation in case_variations:
            response = self.forced_auth_req(
                "get", self.url, data=variation, user=self.partner_staff
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
