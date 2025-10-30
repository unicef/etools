from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import Item, Transfer
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
    fixtures = (
        "poi_type.json",
        "unicef_warehouse.json",
    )

    @classmethod
    def setUpTestData(cls):
        cls.country = CountryFactory()
        cls.partner = PartnerFactory(organization=OrganizationFactory(name="Partner"))
        cls.partner_staff = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION],
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )
        cls.simple_user = SimpleUserFactory()

        cls.url = reverse(f"{ADMIN_PANEL_APP_NAME}:{STOCK_MANAGEMENT_ADMIN_PANEL}-list")

        cls.material_for_update = MaterialFactory(
            other={"uom_map": {"CAR": 1, "BOX": 10}}
        )
        cls.transfer_for_update = TransferFactory(
            status=Transfer.COMPLETED,
            partner_organization=cls.partner,
        )
        cls.item_for_update = ItemFactory(
            transfer=cls.transfer_for_update,
            material=cls.material_for_update,
            quantity=100,
            uom="CAR",
        )
        cls.item_update_url = reverse(
            f"{ADMIN_PANEL_APP_NAME}:{UPDATE_ITEM_STOCK_ADMIN_PANEL}-detail",
            kwargs={"pk": cls.item_for_update.pk},
        )
        cls.non_existent_item_url = reverse(
            f"{ADMIN_PANEL_APP_NAME}:{UPDATE_ITEM_STOCK_ADMIN_PANEL}-detail",
            kwargs={"pk": 99999},
        )

    def test_get_stock_management(self):
        response = self.forced_auth_req("get", self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "'poi_id': ErrorDetail(string='This query parameter is required.",
            str(response.data),
        )

    def test_get_stock_management_unauthorized(self):
        response = self.forced_auth_req("get", self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_stock_management_without_correct_permissions(self):
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff_without_correct_permissions
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_transfer_items_without_poi_id(self):
        # Without poi_id query param, the queryset should be empty.
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
            destination_point=poi,
        )
        ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(results)

    def test_list_transfer_items_with_invalid_poi_id(self):
        payload = {"poi_id": 9999}  # Assuming 9999 does not exist.
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_list_transfer_items_with_hidden_item(self):
        poi = PointOfInterestFactory(name="Hidden Item POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
        )
        ItemFactory(transfer=transfer, hidden=True)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_list_transfer_items_search_filter(self):
        poi = PointOfInterestFactory(name="Search POI")
        transfer1 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="Alpha Order",
        )
        transfer2 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="Beta Order",
        )
        ItemFactory(transfer=transfer1, hidden=False)
        ItemFactory(transfer=transfer2, hidden=False)
        payload = {"poi_id": poi.id, "search": "Alpha"}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)

    # ------------------ CREATE (POST) Tests ------------------

    def test_create_transfer_item_success(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Destination POI"
        )
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "BatchX",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
        payload = {"location": destination.pk}
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("partner_organization", response.data)
        self.assertIn("items", response.data)

    def test_create_transfer_item_empty_items(self):
        destination = PointOfInterestFactory(name="Destination POI Empty Items")
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No items were provided", str(response.data))

    def test_create_transfer_item_invalid_items(self):
        destination = PointOfInterestFactory(name="Destination POI Invalid Items")
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": "",  # Invalid: empty material
                    "quantity": None,  # Invalid: no quantity
                    "uom": "pcs",  # Missing item_name
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchY",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "The partner does not exist under the location.", str(response.data)
        )

    def test_create_transfer_item_missing_location(self):
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 8,
                    "uom": "pcs",
                    "item_name": "BatchZ",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchW",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchU",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.simple_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_transfer_items_completed(self):
        # Create a POI.
        poi = PointOfInterestFactory(name="Completed POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.PENDING,
            partner_organization=self.partner,
            destination_point=poi,
        )
        transfer1 = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
        )
        ItemFactory(transfer=transfer1, hidden=False)
        ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 2)

    def test_list_transfer_items_with_mixed_item_visibility(self):
        # Create a POI.
        poi = PointOfInterestFactory(name="Mixed Visibility POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
        )
        # Create one hidden and one visible item.
        ItemFactory(transfer=transfer, hidden=True)
        item = ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        # Expect the transfer to appear because it has at least one non-hidden item.
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("quantity"), item.quantity)
        self.assertEqual(results[0].get("batch_id"), item.batch_id)
        self.assertEqual(results[0].get("uom"), item.uom)

    def test_list_transfer_items_pagination(self):
        poi = PointOfInterestFactory(name="Pagination POI")
        num_transfers = 15
        for _ in range(num_transfers):
            transfer = TransferFactory(
                origin_point=poi,
                status=Transfer.COMPLETED,
                partner_organization=self.partner,
                destination_point=poi,
            )
            ItemFactory(transfer=transfer, hidden=False)
        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchInvalidMaterial",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchInvalidUOM",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchNonNumeric",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchNegative",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", str(response.data).lower())

    def test_create_transfer_item_extra_fields(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Dest POI Extra Fields"
        )
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
                    "extra_item_field": "ignored too",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_transfer_item_invalid_partner_organization_id(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Dest POI Extra Fields"
        )
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
                    "item_name": "BatchInvalidPartner",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
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
                    "item_name": "BatchInvalidLocation",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", str(response.data).lower())

    def test_retrieve_item_success(self):
        response = self.forced_auth_req(
            "get", self.item_update_url, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], self.item_for_update.quantity)

    def test_retrieve_item_unauthorized(self):
        response = self.forced_auth_req(
            "get", self.item_update_url, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_item_not_found(self):
        response = self.forced_auth_req(
            "get", self.non_existent_item_url, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_success(self):
        payload = {"quantity": 50, "uom": "BOX"}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item_for_update.refresh_from_db()
        self.assertEqual(self.item_for_update.quantity, 50)
        self.assertEqual(self.item_for_update.uom, "BOX")

    def test_partial_update_item_quantity_only(self):
        payload = {"quantity": 75}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item_for_update.refresh_from_db()
        self.assertEqual(self.item_for_update.quantity, 75)
        self.assertEqual(self.item_for_update.uom, "CAR")  # Should not change

    def test_partial_update_item_uom_only(self):
        payload = {"uom": "BOX"}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item_for_update.refresh_from_db()
        self.assertEqual(self.item_for_update.quantity, 100)  # Should not change
        self.assertEqual(self.item_for_update.uom, "BOX")

    def test_update_item_fails_unauthorized(self):
        payload = {"quantity": 50}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.simple_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_item_fails_without_correct_permissions(self):
        payload = {"quantity": 50}
        response = self.forced_auth_req(
            "patch",
            self.item_update_url,
            user=self.partner_staff_without_correct_permissions,
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_item_fails_negative_quantity(self):
        payload = {"quantity": -10}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The quantity must be greater than 0", str(response.data))

    def test_update_item_fails_zero_quantity(self):
        payload = {"quantity": 0}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The quantity must be greater than 0", str(response.data))

    def test_update_item_fails_invalid_uom(self):
        payload = {"uom": "INVALID_UOM"}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is not a valid choice", str(response.data))

    def test_update_item_fails_uom_not_valid_for_material(self):
        payload = {"uom": "PCS"}
        response = self.forced_auth_req(
            "patch", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is not a valid choice.", str(response.data))

    def test_update_item_not_found(self):
        payload = {"quantity": 50}
        response = self.forced_auth_req(
            "patch", self.non_existent_item_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_with_put_success(self):
        payload = {"quantity": 50, "uom": "BOX"}
        response = self.forced_auth_req(
            "put", self.item_update_url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item_for_update.refresh_from_db()
        self.assertEqual(self.item_for_update.quantity, 50)
        self.assertEqual(self.item_for_update.uom, "BOX")

    def test_create_transfer_item_with_unicode_batch_name(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Unicode Destination"
        )
        material = MaterialFactory()
        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "批次أ-测试-🏷️",
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transfer = Transfer.objects.get(pk=response.data.get("id"))
        item = transfer.items.first()
        self.assertEqual(item.batch_id, "批次أ-测试-🏷️")

    def test_create_transfer_item_with_maximum_length_batch_name(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Max Length Destination"
        )
        material = MaterialFactory()
        max_length_batch = "B" * 254

        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": max_length_batch,
                }
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_transfer_item_with_decimal_quantity(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Decimal Qty Destination"
        )
        material = MaterialFactory()
        decimal_quantities = [1.5, 10.75, 0.1, 999.99]

        for i, quantity in enumerate(decimal_quantities):
            payload = {
                "partner_organization": self.partner.pk,
                "location": destination.pk,
                "items": [
                    {
                        "material": material.pk,
                        "quantity": quantity,
                        "uom": "CAR",
                        "item_name": f"DecimalQty{i}",
                    }
                ],
            }
            response = self.forced_auth_req(
                "post", self.url, user=self.partner_staff, data=payload
            )
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
            )

    def test_create_transfer_item_with_multiple_items_same_material(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Multi Item Destination"
        )
        material = MaterialFactory()

        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "Batch1",
                },
                {
                    "material": material.pk,
                    "quantity": 20,
                    "uom": "CAR",
                    "item_name": "Batch2",
                },
                {
                    "material": material.pk,
                    "quantity": 30,
                    "uom": "CAR",
                    "item_name": "Batch3",
                },
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transfer = Transfer.objects.get(pk=response.data.get("id"))
        self.assertEqual(transfer.items.count(), 3)

    def test_create_transfer_item_with_very_large_item_list(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Large List Destination"
        )
        material = MaterialFactory()

        items = []
        for i in range(100):
            items.append(
                {
                    "material": material.pk,
                    "quantity": i + 1,
                    "uom": "CAR",
                    "item_name": f"BatchLarge{i:03d}",
                }
            )

        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": items,
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED])

    def test_create_transfer_item_with_missing_item_fields(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Missing Fields Dest"
        )
        material = MaterialFactory()

        incomplete_items = [
            {"material": material.pk, "quantity": 10, "uom": "CAR"},
            {"material": material.pk, "uom": "CAR", "item_name": "Batch1"},
            {"quantity": 10, "uom": "CAR", "item_name": "Batch2"},
            {"material": material.pk, "quantity": 10, "item_name": "Batch3"},
        ]

        for i, item in enumerate(incomplete_items):
            payload = {
                "partner_organization": self.partner.pk,
                "location": destination.pk,
                "items": [item],
            }
            response = self.forced_auth_req(
                "post", self.url, user=self.partner_staff, data=payload
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Should fail for incomplete item: {item}",
            )

    def test_create_transfer_item_with_empty_string_fields(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Empty String Dest"
        )
        material = MaterialFactory()

        empty_field_items = [
            {"material": material.pk, "quantity": 10, "uom": "CAR", "item_name": ""},
            {"material": material.pk, "quantity": 10, "uom": "", "item_name": "Batch1"},
        ]

        for item in empty_field_items:
            payload = {
                "partner_organization": self.partner.pk,
                "location": destination.pk,
                "items": [item],
            }
            response = self.forced_auth_req(
                "post", self.url, user=self.partner_staff, data=payload
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_unicode_characters(self):
        poi = PointOfInterestFactory(name="Unicode Search POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="الطلب العربي",
        )
        ItemFactory(transfer=transfer, hidden=False)

        payload = {"poi_id": poi.id, "search": "العربي"}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_with_special_characters(self):
        poi = PointOfInterestFactory(name="Special Search POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
            unicef_release_order="Order@#$%^&*()",
        )
        ItemFactory(transfer=transfer, hidden=False)

        special_searches = ["@#$", "%^&", "*()_+", "[]{}|"]
        for search_term in special_searches:
            payload = {"poi_id": poi.id, "search": search_term}
            response = self.forced_auth_req(
                "get", self.url, user=self.partner_staff, data=payload
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_item_with_null_values(self):
        null_payloads = [{"quantity": None}, {"uom": None}]

        for payload in null_payloads:
            response = self.forced_auth_req(
                "patch", self.item_update_url, user=self.partner_staff, data=payload
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_transfer_items_with_malformed_filter_parameters(self):
        poi = PointOfInterestFactory(name="Malformed Filter POI")
        malformed_filters = [
            {"poi_id": poi.id, "search": "test", "extra_param": "should_be_ignored"},
            {"poi_id": poi.id, "offset": "not_a_number"},
            {"poi_id": poi.id, "limit": -1},
            {"poi_id": poi.id, "ordering": "nonexistent_field"},
        ]

        for filters in malformed_filters:
            response = self.forced_auth_req(
                "get", self.url, user=self.partner_staff, data=filters
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_transfer_item_with_duplicate_batch_names(self):
        destination = PointOfInterestFactory(
            partner_organizations=[self.partner], name="Duplicate Batch Dest"
        )
        material = MaterialFactory()

        payload = {
            "partner_organization": self.partner.pk,
            "location": destination.pk,
            "items": [
                {
                    "material": material.pk,
                    "quantity": 10,
                    "uom": "CAR",
                    "item_name": "DuplicateBatch",
                },
                {
                    "material": material.pk,
                    "quantity": 20,
                    "uom": "CAR",
                    "item_name": "DuplicateBatch",
                },
            ],
        }
        response = self.forced_auth_req(
            "post", self.url, user=self.partner_staff, data=payload
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED])

    def test_item_visibility_edge_cases(self):
        poi = PointOfInterestFactory(name="Visibility Edge POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
        )

        visible_item = ItemFactory(transfer=transfer, hidden=False)
        hidden_item = ItemFactory(transfer=transfer, hidden=True)

        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get("results", [])
        returned_item_ids = [r.get("id") for r in results]
        self.assertIn(visible_item.id, returned_item_ids)
        self.assertNotIn(hidden_item.id, returned_item_ids)

    def test_item_marked_as_hidden_after_soft_delete(self):
        item_id = self.item_for_update.id
        self.assertFalse(self.item_for_update.hidden)
        response = self.forced_auth_req(
            "delete", self.item_update_url, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(ObjectDoesNotExist):
            Item.objects.get(id=item_id)

    def test_soft_delete_item_unauthorized(self):
        response = self.forced_auth_req(
            "delete", self.item_update_url, user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_delete_item_without_correct_permissions(self):
        response = self.forced_auth_req(
            "delete", self.item_update_url, user=self.partner_staff_without_correct_permissions
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_delete_non_existent_item(self):
        response = self.forced_auth_req(
            "delete", self.non_existent_item_url, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_deleted_item_not_in_default_queryset(self):
        item_id = self.item_for_update.id
        self.assertTrue(Item.objects.filter(id=item_id).exists())
        response = self.forced_auth_req(
            "delete", self.item_update_url, user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Item.objects.filter(id=item_id).exists())

    def test_multiple_items_soft_delete_transfer_visibility(self):
        poi = PointOfInterestFactory(name="Multi Delete POI")
        transfer = TransferFactory(
            origin_point=poi,
            status=Transfer.COMPLETED,
            partner_organization=self.partner,
            destination_point=poi,
        )
        item1 = ItemFactory(transfer=transfer, hidden=False)
        item2 = ItemFactory(transfer=transfer, hidden=False)

        item1_url = reverse(
            f"{ADMIN_PANEL_APP_NAME}:{UPDATE_ITEM_STOCK_ADMIN_PANEL}-detail",
            kwargs={"pk": item1.pk},
        )
        item2_url = reverse(
            f"{ADMIN_PANEL_APP_NAME}:{UPDATE_ITEM_STOCK_ADMIN_PANEL}-detail",
            kwargs={"pk": item2.pk},
        )

        payload = {"poi_id": poi.id}
        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        initial_count = len(response.data.get("results", []))

        self.forced_auth_req("delete", item1_url, user=self.partner_staff)

        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(len(response.data.get("results", [])), initial_count - 1)

        self.forced_auth_req("delete", item2_url, user=self.partner_staff)

        response = self.forced_auth_req(
            "get", self.url, user=self.partner_staff, data=payload
        )
        self.assertEqual(len(response.data.get("results", [])), initial_count - 2)

    def test_export_csv(self):
        response = self.forced_auth_req('get', reverse(f"{ADMIN_PANEL_APP_NAME}:{LOCATIONS_ADMIN_PANEL}-list") + "export/csv/", user=self.partner_staff)
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

        self.assertIn('Transfer Name', content)
        self.assertIn('Transfer Reference', content)
        self.assertIn('Item ID', content)
        self.assertIn('Item Name', content)
        self.assertIn('Item Quantity', content)
