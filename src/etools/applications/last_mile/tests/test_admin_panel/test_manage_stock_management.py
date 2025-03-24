from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import Transfer
from etools.applications.last_mile.tests.factories import (
    ItemFactory,
    MaterialFactory,
    PointOfInterestFactory,
    TransferFactory,
)
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import CountryFactory, SimpleUserFactory, UserPermissionFactory


class TestStockManagementViewSet(BaseTenantTestCase):
    fixtures = ('poi_type.json', 'unicef_warehouse.json',)

    @classmethod
    def setUpTestData(cls):
        cls.country = CountryFactory()
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.simple_user = SimpleUserFactory()

        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{STOCK_MANAGEMENT_ADMIN_PANEL}-list')

    def test_get_stock_management(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_stock_management_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_stock_management_without_correct_permissions(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_transfer_items_without_poi_id(self):
        # Without poi_id query param, the queryset should be empty.
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_list_transfer_items_with_valid_poi_id(self):
        # Create a PointOfInterest using the factory.
        poi = PointOfInterestFactory(name="Test POI")
        # Create a Transfer that meets filter criteria:
        # - status must be COMPLETED
        # - origin_point's id equals poi.id
        # - It must have at least one non-hidden item.
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi
        )
        ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(results[0].get("items"))

    def test_list_transfer_items_with_invalid_poi_id(self):
        payload = {"poi_id": 9999}  # Assuming 9999 does not exist.
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_list_transfer_items_with_hidden_item(self):
        poi = PointOfInterestFactory(name="Hidden Item POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi
        )
        ItemFactory(transfer=transfer, hidden=True)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_list_transfer_items_search_filter(self):
        poi = PointOfInterestFactory(name="Search POI")
        transfer1 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="Alpha Order"
        )
        transfer2 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="Beta Order"
        )
        ItemFactory(transfer=transfer1, hidden=False)
        ItemFactory(transfer=transfer2, hidden=False)
        payload = {"poi_id": poi.id, "search": "Alpha"}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)

    # ------------------ CREATE (POST) Tests ------------------

    def test_create_transfer_item_success(self):
        destination = PointOfInterestFactory(partner_organizations=[self.partner], name="Destination POI")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchX"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transfer_id = response.data.get("id")
        self.assertIsNotNone(transfer_id)
        transfer = Transfer.objects.get(pk=transfer_id)
        self.assertEqual(transfer.partner_organization.pk, self.partner.pk)
        self.assertEqual(transfer.destination_point.pk, destination.pk)
        self.assertGreater(transfer.items.count(), 0)
        created_item = transfer.items.first()
        self.assertEqual(created_item.batch_id, "BatchX")
        self.assertEqual(created_item.quantity, 10)

    def test_create_transfer_item_missing_fields(self):
        # Missing partner_organization and items.
        destination = PointOfInterestFactory(name="Destination POI Missing Fields")
        payload = {
            "location": destination.pk
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("partner_organization", response.data)
        self.assertIn("items", response.data)

    def test_create_transfer_item_empty_items(self):
        destination = PointOfInterestFactory(name="Destination POI Empty Items")
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": []
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No items were provided", str(response.data))

    def test_create_transfer_item_invalid_items(self):
        destination = PointOfInterestFactory(name="Destination POI Invalid Items")
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": "",       # Invalid: empty material
                    "quantity": None,     # Invalid: no quantity
                    "uom": "pcs"          # Missing item_name
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_create_transfer_item_invalid_partner_location(self):
        # Simulate an invalid partner location.
        destination = PointOfInterestFactory(name="Invalid Destination")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 5,
                    "uom": "BAG",
                    "item_name": "BatchY"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The partner does not exist under the location.", str(response.data))

    def test_create_transfer_item_missing_location(self):
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 8,
                    "uom": "pcs",
                    "item_name": "BatchZ"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", response.data)

    def test_create_transfer_item_missing_partner_organization(self):
        destination = PointOfInterestFactory(name="Destination POI Missing Org")
        material = MaterialFactory()
        payload = {
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 12,
                    "uom": "pcs",
                    "item_name": "BatchW"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("partner_organization", response.data)

    def test_create_transfer_item_unauthorized(self):
        destination = PointOfInterestFactory(name="Destination POI Unauthorized")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 20,
                    "uom": "pcs",
                    "item_name": "BatchU"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.simple_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_transfer_items_completed(self):
        # Create a POI.
        poi = PointOfInterestFactory(name="Completed POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.PENDING,
            partner_organization=self.partner,
            destination_point=poi
        )
        transfer1 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi
        )
        ItemFactory(transfer=transfer1, hidden=False)
        ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 2)

    def test_list_transfer_items_with_mixed_item_visibility(self):
        # Create a POI.
        poi = PointOfInterestFactory(name="Mixed Visibility POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi
        )
        # Create one hidden and one visible item.
        ItemFactory(transfer=transfer, hidden=True)
        ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        # Expect the transfer to appear because it has at least one non-hidden item.
        self.assertEqual(len(results), 1)
        self.assertTrue(len(results[0].get("items", [])) > 0)

    def test_list_transfer_items_pagination(self):
        poi = PointOfInterestFactory(name="Pagination POI")
        num_transfers = 15
        for _ in range(num_transfers):
            transfer = TransferFactory(
                origin_point=poi,
                status=Transfer.COMPLETED,
                partner_organization=self.partner,
                destination_point=poi
            )
            ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination keys.
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertEqual(response.data.get("count"), num_transfers)

    def test_create_transfer_item_invalid_material(self):
        destination = PointOfInterestFactory(name="Dest POI Invalid Material")
        invalid_material_id = 9999  # Assuming this ID does not exist.
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": invalid_material_id,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchInvalidMaterial"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("material", str(response.data).lower())

    def test_create_transfer_item_invalid_uom(self):
        destination = PointOfInterestFactory(name="Dest POI Invalid UOM")
        material = MaterialFactory()
        invalid_uom = "InvalidUOM"
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": invalid_uom,
                    "item_name": "BatchInvalidUOM"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uom", str(response.data).lower())

    def test_create_transfer_item_non_numeric_quantity(self):
        destination = PointOfInterestFactory(name="Dest POI Non-Numeric Quantity")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": "ten",  # Non-numeric quantity.
                    "uom": "CAR",
                    "item_name": "BatchNonNumeric"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", str(response.data).lower())

    def test_create_transfer_item_negative_quantity(self):
        destination = PointOfInterestFactory(name="Dest POI Negative Quantity")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": -5,  # Negative quantity.
                    "uom": "CAR",
                    "item_name": "BatchNegative"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", str(response.data).lower())

    def test_create_transfer_item_extra_fields(self):
        destination = PointOfInterestFactory(partner_organizations=[self.partner], name="Dest POI Extra Fields")
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "extra_field": "should be ignored",
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchExtra",
                    "extra_item_field": "ignored too"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_transfer_item_invalid_partner_organization_id(self):
        destination = PointOfInterestFactory(partner_organizations=[self.partner], name="Dest POI Extra Fields")
        material = MaterialFactory()
        invalid_partner_id = 9999  # Assuming this ID does not exist.
        payload = {
            "partner_organization": invalid_partner_id,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchInvalidPartner"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("partner_organization", str(response.data).lower())

    def test_create_transfer_item_invalid_location_id(self):
        material = MaterialFactory()
        invalid_location_id = 9999  # Assuming this ID does not exist.
        payload = {
            "partner_organization": self.partner.pk,
            "location": invalid_location_id,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchInvalidLocation"
                }
            ]
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", str(response.data).lower())
