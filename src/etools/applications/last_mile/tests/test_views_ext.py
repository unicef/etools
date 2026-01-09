import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from applications.last_mile.tests.factories import (
    ItemAuditConfigurationFactory,
    ItemFactory,
    ItemTransferHistoryFactory,
    MaterialFactory,
    PointOfInterestFactory,
    PointOfInterestTypeFactory,
    TransferFactory,
)
from freezegun import freeze_time
from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.last_mile import models
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.models import Country, Realm
from etools.applications.users.tests.factories import UserFactory


class TestVisionIngestTransfersApiView(BaseTenantTestCase):
    url = reverse("last_mile:vision-ingest-transfers")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.unicef_warehouse = PointOfInterestFactory(
            id=1, name="UNICEF Main Warehouse"
        )

        cls.partner_org1 = OrganizationFactory(vendor_number="IP12345")
        cls.partner1 = PartnerFactory(organization=cls.partner_org1)

        cls.partner_org2 = OrganizationFactory(vendor_number="IP67890")
        cls.partner2 = PartnerFactory(organization=cls.partner_org2)

        cls.org_without_partner = OrganizationFactory(
            vendor_number="NO_PARTNER_PROFILE"
        )

        cls.material1 = MaterialFactory(number="MAT-001", short_description="Biscuits")
        cls.material2 = MaterialFactory(
            number="MAT-002", short_description="Water Tablets"
        )

    def test_correct_tenant(self):
        self.assertEqual(self.api_user.profile.country.schema_name, "test")
        self.assertEqual(connection.tenant.schema_name, "test")

    def test_unauthenticated_request_fails(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-126",
                "PONumber": "PO-99999",
                "EtoolsReference": "PD/SDA/2023/999",
                "WaybillNumber": "WB-IGNORE-000",
                "DocumentCreationDate": "2023-11-05T09:00:00Z",
                "ImplementingPartner": "U39205",
                "ReleaseOrderItem": "00010",
                "MaterialNumber": "TESTMATERIAL#002",
                "ItemDescription": "This item will be ignored",
                "Quantity": 1,
                "UOM": "EA",
                "ExpiryDate": "null",
                "POItem": "0001",
                "AmountUSD": 1.00,
                "HandoverNumber": "null",
                "HandoverItem": "null",
                "HandoverYear": "null",
                "Plant": "null",
                "PurchaseOrderType": "null",
            }
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.unauthorized_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_successful_ingest_creates_transfer_and_items(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-A1",
                "ImplementingPartner": "IP12345",
                "PONumber": "PO-111",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "ItemDescription": "This item will be ignored",
                "Quantity": 100,
                "UOM": "BOX",
                "BatchNumber": "B1",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-A1",
                "ImplementingPartner": "IP12345",
                "PONumber": "PO-111",
                "MaterialNumber": "MAT-002",
                "ItemDescription": "This item will be ignored",
                "ReleaseOrderItem": "20",
                "Quantity": 200,
                "UOM": "PAC",
                "BatchNumber": "B2",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 2)

        transfer = models.Transfer.objects.first()
        self.assertEqual(transfer.unicef_release_order, "RO-A1")
        self.assertEqual(transfer.purchase_order_id, "PO-111")
        self.assertEqual(transfer.partner_organization, self.partner1)
        self.assertEqual(transfer.origin_point.pk, self.unicef_warehouse.pk)
        self.assertEqual(transfer.items.count(), 2)

        item1 = models.Item.objects.get(unicef_ro_item="10")
        self.assertEqual(item1.material, self.material1)
        self.assertEqual(item1.quantity, 100)

    def test_ingest_adds_items_to_existing_transfer(self):
        existing_transfer = TransferFactory(
            unicef_release_order="RO-EXISTING", partner_organization=self.partner1
        )
        self.assertEqual(models.Transfer.objects.count(), 1)

        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-EXISTING",
                "ImplementingPartner": "IP12345",
                "ItemDescription": "This item will be ignored",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "30",
                "UOM": "EA",
                "Quantity": 50,
                "BatchNumber": "B3",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(existing_transfer.items.count(), 1)
        self.assertEqual(models.Item.objects.first().unicef_ro_item, "30")

    def test_ingest_skips_row_if_partner_not_found(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-FAIL",
                "ImplementingPartner": "IP_DOES_NOT_EXIST",
                "MaterialNumber": "MAT-001",
                "ItemDescription": "This item will be ignored",
                "ReleaseOrderItem": "10",
                "UOM": "EA",
                "Quantity": 10,
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_ingest_skips_row_if_organization_has_no_partner_profile(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-FAIL",
                "ImplementingPartner": "NO_PARTNER_PROFILE",
                "MaterialNumber": "MAT-001",
                "ItemDescription": "This item will be ignored",
                "ReleaseOrderItem": "10",
                "UOM": "EA",
                "Quantity": 10,
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_ingest_skips_item_if_material_not_found(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-PARTIAL",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "ItemDescription": "This item will be ignored",
                "Quantity": 100,
                "UOM": "EA",
                "BatchNumber": "B1",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-PARTIAL",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "INVALID-MATERIAL",
                "ReleaseOrderItem": "20",
                "ItemDescription": "This item will be ignored",
                "Quantity": 200,
                "UOM": "EA",
                "BatchNumber": "B2",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(models.Item.objects.first().material, self.material1)

    def test_idempotency_duplicate_payload_does_not_create_new_objects(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-IDEMPOTENT",
                "ImplementingPartner": "IP12345",
                "ItemDescription": "This item will be ignored",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "UOM": "EA",
                "BatchNumber": "B1",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

    def test_import_with_null_batch_number(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-NULL-BATCH",
                "ImplementingPartner": "IP12345",
                "ItemDescription": "This item will be ignored",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "UOM": "EA",
                "BatchNumber": None,
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

    def test_rows_with_incorrect_event_are_ignored(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-GOOD",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "ItemDescription": "This item will be ignored",
                "UOM": "EA",
            },
            {
                "Event": "AR",
                "ReleaseOrder": "RO-BAD",
                "ImplementingPartner": "IP67890",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 20,
                "BatchNumber": "B2",
                "ItemDescription": "This item will be ignored",
                "UOM": "EA",
            },
            {
                "Event": "OTHER",
                "ReleaseOrder": "RO-BAD",
                "ImplementingPartner": "IP67890",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "30",
                "Quantity": 30,
                "BatchNumber": "B3",
                "ItemDescription": "This item will be ignored",
                "UOM": "EA",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(
            models.Transfer.objects.first().unicef_release_order, "RO-GOOD"
        )

    def test_html_tags_are_stripped_and_other_fields_are_saved(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-CLEAN",
                "ImplementingPartner": "IP12345",
                "PONumber": "<p>PO-CLEAN</p>",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "ItemDescription": "Item with <b>bold</b> text",
                "Quantity": 1,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ExpiryDate": "2025-12-31",
                "HandoverNumber": "HO-123",
                "Plant": "PL-01",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        transfer = models.Transfer.objects.first()
        self.assertEqual(transfer.purchase_order_id, "PO-CLEAN")

        item = models.Item.objects.first()

        self.assertIsNotNone(item.expiry_date)

        self.assertEqual(item.other["HandoverNumber"], "HO-123")
        self.assertEqual(item.other["Plant"], "PL-01")
        self.assertEqual(item.other["itemid"], "RO-CLEAN-10")

    def test_item_without_batch_id_gets_defaults(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-NOBATCH",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "ItemDescription": "This item will be ignored",
                "Quantity": 15,
                "UOM": "EA",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = models.Item.objects.first()
        self.assertEqual(item.quantity, 15)
        self.assertEqual(item.uom, "EA")
        self.assertEqual(item.conversion_factor, 1.0)

    def test_permission_denied_for_authenticated_non_api_user(self):
        regular_user = UserFactory()

        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-DENIED",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
            }
        ]

        response = self.forced_auth_req(
            "post", self.url, user=regular_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(models.Transfer.objects.count(), 0)

    def test_graceful_handling_of_empty_payload(self):
        payload = []

        response = self.forced_auth_req(
            "post", self.url, user=self.api_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_graceful_handling_of_fully_invalid_payload(self):
        payload = [
            {
                "Event": "AR",
                "ReleaseOrder": "RO-BAD-1",
                "ImplementingPartner": "IP12345",
            },
            {
                "Event": "XX",
                "ReleaseOrder": "RO-BAD-2",
                "ImplementingPartner": "IP12345",
            },
        ]

        response = self.forced_auth_req(
            "post", self.url, user=self.api_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_uom_is_popped_when_matching_material_original_uom(self):
        self.material1.original_uom = "BOX"
        self.material1.uom = "EA"
        self.material1.save()

        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-UOM-TEST",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 50,
                "ItemDescription": "This item will be ignored",
                "UOM": "BOX",
                "BatchNumber": "B-UOM",
            }
        ]

        response = self.forced_auth_req(
            "post", self.url, user=self.api_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = models.Item.objects.first()
        self.assertEqual(item.uom, None)

    def test_robustness_with_numeric_fields_as_strings(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-STRING-NUM",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": "150",
                "AmountUSD": "350.55",
                "BatchNumber": "B1",
                "ItemDescription": "This item will be ignored",
                "UOM": "EA",
            }
        ]

        response = self.forced_auth_req(
            "post", self.url, user=self.api_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = models.Item.objects.first()
        self.assertEqual(item.quantity, 150)
        self.assertEqual(item.amount_usd, Decimal("350.55"))

    def test_validation_error_on_missing_required_field(self):
        payload = [
            {
                # "ReleaseOrder": "RO-MISSING",  <-- Missing required field
                "Event": "LD",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "description",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ReleaseOrder", response.data[0])
        self.assertEqual(response.data[0]["ReleaseOrder"][0].code, "required")
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_validation_error_on_malformed_data(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-BAD-DATA",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": "this-is-not-a-number",
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "description",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Quantity", response.data[0])
        self.assertEqual(response.data[0]["Quantity"][0].code, "invalid")
        self.assertEqual(models.Item.objects.count(), 0)

    def test_response_structure_on_full_success(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-A1",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 100,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-A1",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 200,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_response = {
            "status": "Completed",
            "transfers_created": 1,
            "items_created": 2,
            "skipped_count": 0,
            "details": {"skipped_transfers": [], "skipped_items": []},
        }
        self.assertEqual(response.data, expected_response)

    def test_partial_ingest_with_skipped_items_reported_in_response(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-PARTIAL",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 100,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-PARTIAL",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "INVALID-MATERIAL",
                "ReleaseOrderItem": "20",
                "Quantity": 200,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data["transfers_created"], 1)
        self.assertEqual(response.data["items_created"], 1)
        self.assertEqual(response.data["skipped_count"], 1)
        self.assertEqual(len(response.data["details"]["skipped_items"]), 1)

        skipped_report = response.data["details"]["skipped_items"][0]
        self.assertEqual(
            skipped_report["reason"], "Material number 'INVALID-MATERIAL' not found."
        )
        self.assertEqual(skipped_report["item"]["material_number"], "INVALID-MATERIAL")

    def test_idempotency_reports_skipped_items_on_second_run(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-IDEMPOTENT",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            }
        ]

        first_response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data["items_created"], 1)
        self.assertEqual(first_response.data["skipped_count"], 0)
        self.assertEqual(models.Item.objects.count(), 1)

        second_response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(second_response.data["items_created"], 0)
        self.assertEqual(second_response.data["skipped_count"], 1)
        self.assertEqual(len(second_response.data["details"]["skipped_items"]), 1)
        self.assertEqual(
            second_response.data["details"]["skipped_items"][0]["reason"],
            "Duplicate item found in database.",
        )

    def test_multiple_new_transfers_in_one_payload(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-MULTI-1",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-MULTI-2",
                "ImplementingPartner": "IP67890",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "10",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 2)

        self.assertEqual(response.data["transfers_created"], 2)
        self.assertEqual(response.data["items_created"], 2)
        self.assertEqual(response.data["skipped_count"], 0)

    def test_duplicate_item_within_payload_is_skipped_and_reported(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-DUP-ITEM",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 100,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-DUP-ITEM",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "10",
                "Quantity": 200,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data["items_created"], 1)
        self.assertEqual(response.data["skipped_count"], 1)
        self.assertEqual(len(response.data["details"]["skipped_items"]), 1)

        skipped_report = response.data["details"]["skipped_items"][0]
        self.assertEqual(
            skipped_report["reason"], "Duplicate item found within the same payload."
        )
        self.assertEqual(skipped_report["item"]["unicef_ro_item"], "10")

    def test_payload_with_conflicting_partners_for_same_release_order(self):
        """
        Tests that if a payload contains conflicting ImplementingPartners for the same
        ReleaseOrder, the system creates only ONE transfer using the first partner it
        encounters and adds all items to it.
        """
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-CONFLICT",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-CONFLICT",
                "ImplementingPartner": "IP67890",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 2)

        transfer = models.Transfer.objects.first()
        self.assertEqual(transfer.partner_organization, self.partner1)
        self.assertEqual(transfer.items.count(), 2)

        self.assertEqual(response.data["transfers_created"], 1)
        self.assertEqual(response.data["items_created"], 2)
        self.assertEqual(response.data["skipped_count"], 0)

    def test_all_transfers_fail_no_items_are_created(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-FAIL-1",
                "ImplementingPartner": "BAD_IP_1",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-FAIL-2",
                "ImplementingPartner": "BAD_IP_2",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

        self.assertEqual(response.data["transfers_created"], 0)
        self.assertEqual(response.data["items_created"], 0)
        self.assertEqual(response.data["skipped_count"], 2)
        self.assertEqual(len(response.data["details"]["skipped_transfers"]), 2)
        self.assertEqual(len(response.data["details"]["skipped_items"]), 0)
        self.assertIn("RO-FAIL-1", str(response.data["details"]["skipped_transfers"]))
        self.assertIn("RO-FAIL-2", str(response.data["details"]["skipped_transfers"]))

    def test_graceful_handling_of_payload_with_no_ld_events(self):
        payload = [
            {
                "Event": "AR",
                "ReleaseOrder": "RO-IGNORE-1",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "GR",
                "ReleaseOrder": "RO-IGNORE-2",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(
            response.data["detail"], "No rows with Event 'LD' found in the payload."
        )

    def test_create_transfer_with_items_wrong_uom(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-IGNORE-1",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "CAAR",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-IGNORE-2",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "20",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "CAR",
                "ItemDescription": "d",
            },
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data["transfers_created"], 2)
        self.assertEqual(response.data["items_created"], 1)
        self.assertEqual(response.data["skipped_count"], 1)
        self.assertEqual(
            response.data["details"]["skipped_items"][0]["reason"],
            "UOM 'CAAR' not valid.",
        )

    def test_mixed_payload_creates_new_and_adds_to_existing_transfer(self):
        existing_transfer = TransferFactory(
            unicef_release_order="RO-EXISTING", partner_organization=self.partner1
        )
        self.assertEqual(models.Transfer.objects.count(), 1)

        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-EXISTING",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 10,
                "BatchNumber": "B1",
                "UOM": "EA",
                "ItemDescription": "d",
            },
            {
                "Event": "LD",
                "ReleaseOrder": "RO-NEW",
                "ImplementingPartner": "IP67890",
                "MaterialNumber": "MAT-002",
                "ReleaseOrderItem": "10",
                "Quantity": 20,
                "BatchNumber": "B2",
                "UOM": "EA",
                "ItemDescription": "d",
            },
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 2)

        self.assertEqual(response.data["transfers_created"], 1)
        self.assertEqual(response.data["items_created"], 2)
        self.assertEqual(response.data["skipped_count"], 0)

        self.assertEqual(existing_transfer.items.count(), 1)
        new_transfer = models.Transfer.objects.get(unicef_release_order="RO-NEW")
        self.assertEqual(new_transfer.items.count(), 1)
        self.assertEqual(new_transfer.partner_organization, self.partner2)

    def test_item_with_uom_ea_gets_conversion_factor_one(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-EA-UOM",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "10",
                "Quantity": 100,
                "BatchNumber": "B-EA-TEST",
                "UOM": "EA",
                "ItemDescription": "Test item with EA UOM",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Item.objects.count(), 1)

        item = models.Item.objects.first()
        self.assertEqual(item.uom, "EA")
        self.assertEqual(item.conversion_factor, 1.0)

    def test_item_with_uom_ea_and_batch_id_gets_conversion_factor_one(self):
        payload = [
            {
                "Event": "LD",
                "ReleaseOrder": "RO-EA-BATCH",
                "ImplementingPartner": "IP12345",
                "MaterialNumber": "MAT-001",
                "ReleaseOrderItem": "20",
                "Quantity": 50,
                "BatchNumber": "BATCH-123",
                "UOM": "EA",
                "ItemDescription": "Test item with EA UOM and batch",
            }
        ]

        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Item.objects.count(), 1)

        item = models.Item.objects.first()
        self.assertEqual(item.uom, "EA")
        self.assertEqual(item.conversion_factor, 1.0)
        self.assertIsNotNone(item.batch_id)


class TestVisionIngestMaterialsApiView(BaseTenantTestCase):

    url = reverse("last_mile:vision-ingest-materials")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.existing_material = MaterialFactory(
            number="EXISTING-MAT-001", short_description="An already existing material"
        )

    def test_permission_denied_for_non_api_user(self):
        payload = [{"MaterialNumber": "NEW-MAT-001"}]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.unauthorized_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(models.Material.objects.filter(number="NEW-MAT-001").exists())

    def test_other_http_methods_are_disallowed(self):
        self.client.force_authenticate(self.api_user)
        response_get = self.client.get(self.url)
        self.assertEqual(response_get.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response_put = self.client.put(self.url, data={}, format="json")
        self.assertEqual(response_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_successful_ingest_creates_materials(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "MAT-A1", "ShortDescription": "Material A1"},
            {"MaterialNumber": "MAT-B2", "ShortDescription": "Material B2"},
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 2)

        response_data = response.data
        self.assertEqual(response_data["created_count"], 2)
        self.assertEqual(response_data["skipped_count"], 0)
        self.assertEqual(len(response_data["details"]["skipped_existing_in_db"]), 0)
        self.assertEqual(
            len(response_data["details"]["skipped_duplicate_in_payload"]), 0
        )

        self.assertTrue(
            models.Material.objects.filter(
                number="MAT-A1", short_description="Material A1"
            ).exists()
        )

    def test_idempotency_existing_material_is_skipped(self):
        initial_count = models.Material.objects.count()
        payload = [
            {
                "MaterialNumber": self.existing_material.number,
                "ShortDescription": "Updated but should be ignored",
            },
            {
                "MaterialNumber": "MAT-NEW-IDEMPOTENT",
                "ShortDescription": "A new material",
            },
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 1)

        response_data = response.data
        self.assertEqual(response_data["created_count"], 1)
        self.assertEqual(response_data["skipped_count"], 1)
        self.assertIn(
            self.existing_material.number,
            response_data["details"]["skipped_existing_in_db"],
        )

        self.existing_material.refresh_from_db()
        self.assertEqual(
            self.existing_material.short_description, "An already existing material"
        )

    def test_ingest_handles_duplicates_within_payload(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "DUP-IN-PAYLOAD", "ShortDescription": "First instance"},
            {"MaterialNumber": "MAT-UNIQUE", "ShortDescription": "Another material"},
            {
                "MaterialNumber": "DUP-IN-PAYLOAD",
                "ShortDescription": "Second instance (should be ignored)",
            },
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 2)

        response_data = response.data
        self.assertEqual(response_data["created_count"], 2)
        self.assertEqual(response_data["skipped_count"], 1)
        self.assertIn(
            "DUP-IN-PAYLOAD", response_data["details"]["skipped_duplicate_in_payload"]
        )

    def test_ingest_with_mixed_payload_of_new_and_duplicates(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "NEW-MAT-1"},
            {"MaterialNumber": self.existing_material.number},
            {"MaterialNumber": "DUP-MAT-1"},
            {"MaterialNumber": "NEW-MAT-2"},
            {"MaterialNumber": "DUP-MAT-1"},
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 3)

        response_data = response.data
        self.assertEqual(response_data["created_count"], 3)
        self.assertEqual(response_data["skipped_count"], 2)
        self.assertEqual(
            response_data["details"]["skipped_existing_in_db"],
            [self.existing_material.number],
        )
        self.assertEqual(
            response_data["details"]["skipped_duplicate_in_payload"], ["DUP-MAT-1"]
        )

    def test_html_tags_are_stripped_from_fields(self):
        payload = [{"MaterialNumber": "MAT-CLEAN", "ShortDescription": "<b>Bold</b>"}]
        self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        material = models.Material.objects.get(number="MAT-CLEAN")
        self.assertEqual(material.short_description, "Bold")

    def test_ingest_fails_if_any_item_is_missing_material_number(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "MAT-VALID-1"},
            {"ShortDescription": "This item is missing the material number."},
        ]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.data
        self.assertIsInstance(response_data, list)
        self.assertEqual(len(response_data), 2)
        self.assertEqual(
            response_data[1], {"MaterialNumber": ["This field is required."]}
        )
        self.assertEqual(models.Material.objects.count(), initial_count)

    def test_graceful_handling_of_empty_payload(self):
        initial_count = models.Material.objects.count()
        response = self.forced_auth_req(
            method="post", url=self.url, data=[], user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count)

        response_data = response.data
        self.assertEqual(response_data["created_count"], 0)
        self.assertEqual(response_data["skipped_count"], 0)

    def test_invalid_payload_format_not_a_list_fails(self):
        payload = {"MaterialNumber": "MAT-FAIL"}
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Expected a list of items but got type", str(response.data))

    def test_invalid_payload_format_list_with_non_dict_fails(self):
        payload = [{"MaterialNumber": "MAT-OK"}, "i-am-not-a-dict"]
        response = self.forced_auth_req(
            method="post", url=self.url, data=payload, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Invalid data. Expected a dictionary, but got str", str(response.data[1])
        )


class TestVisionLMSMExport(BaseTenantTestCase):
    url = reverse("last_mile:vision-export-data")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.split_time = timezone.now()

        with freeze_time(cls.split_time - timedelta(days=1)):
            cls.old_transfer = TransferFactory()
            cls.old_poi = PointOfInterestFactory()
            cls.old_item = ItemFactory()
            cls.old_item_history = ItemTransferHistoryFactory()
            cls.old_poi_type = PointOfInterestTypeFactory()

        with freeze_time(cls.split_time + timedelta(days=1)):
            cls.new_transfer = TransferFactory()
            cls.new_poi = PointOfInterestFactory()
            cls.new_item = ItemFactory()
            cls.new_item_history = ItemTransferHistoryFactory()
            cls.new_poi_type = PointOfInterestTypeFactory()

    def _get_and_decode_streaming_response(self, response):
        content_bytes = b"".join(response.streaming_content)
        if not content_bytes:
            return None
        return json.loads(content_bytes.decode("utf-8"))

    def test_permission_denied_for_non_api_user(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "transfer"},
            user=self.unauthorized_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_http_methods_are_disallowed(self):
        self.client.force_authenticate(self.api_user)
        response_post = self.client.post(self.url, data={"type": "transfer"})
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_request_fails_if_type_param_is_missing(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"type": "This field is required."})

    def test_request_fails_if_type_param_is_invalid(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "invalid_model"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"type": "'invalid_model' is not a valid data model type."}
        )

    def test_request_fails_for_invalid_last_modified_format(self):
        params = {"type": "transfer", "last_modified": "not-a-valid-date"}
        response = self.forced_auth_req(
            method="get", url=self.url, data=params, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"last_modified": "Invalid ISO 8601 format for 'last_modified'."},
        )

    def test_export_all_transfers(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={"type": "transfer"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), models.Transfer.objects.count())
        self.assertEqual(len(data), 8)

    def test_export_all_pois(self):
        PointOfInterestFactory(is_active=False)
        PointOfInterestFactory(is_active=False)
        PointOfInterestFactory(is_active=True)
        response = self.forced_auth_req(
            method="get", url=self.url, data={"type": "poi"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data) + 2, models.PointOfInterest.all_objects.count())
        self.assertEqual(len(data), 19)

    def test_export_all_items(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={"type": "item"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), models.Item.objects.count())
        self.assertEqual(len(data), 4)

    def test_export_filtered_transfers_by_last_modified(self):
        params = {"type": "transfer", "last_modified": self.split_time.isoformat()}
        response = self.forced_auth_req(
            method="get", url=self.url, data=params, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 4)

    def test_export_filtered_pois_by_last_modified(self):
        params = {"type": "poi", "last_modified": self.split_time.isoformat()}
        response = self.forced_auth_req(
            method="get", url=self.url, data=params, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 9)

    def test_export_filtered_items_by_last_modified(self):
        params = {"type": "item", "last_modified": self.split_time.isoformat()}
        response = self.forced_auth_req(
            method="get", url=self.url, data=params, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], self.new_item.id)

    def test_export_returns_empty_list_for_filter_with_no_results(self):
        future_time = (timezone.now() + timedelta(days=30)).isoformat()
        params = {"type": "item", "last_modified": future_time}
        response = self.forced_auth_req(
            method="get", url=self.url, data=params, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(data, [])

    def test_export_returns_empty_list_for_model_with_no_data(self):
        models.Transfer.objects.all().delete()
        self.assertEqual(models.Transfer.objects.count(), 0)

        response = self.forced_auth_req(
            method="get", url=self.url, data={"type": "transfer"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(data, [])


class TestVisionUsersExport(BaseTenantTestCase):
    url = reverse("last_mile:users-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.api_user = UserFactory(is_superuser=True, email="api@unicef.org")
        cls.unauthorized_user = UserFactory(
            is_superuser=False, email="regular@example.com"
        )

        cls.test_country = Country.objects.get(schema_name="test")
        cls.test_country.name = "test"
        cls.test_country.save()
        cls.test_country.refresh_from_db()

        cls.ip_lm_editor, _ = Group.objects.get_or_create(name="IP LM Editor")
        cls.driver, _ = Group.objects.get_or_create(name="Driver")
        cls.admin_role, _ = Group.objects.get_or_create(name="Admin")
        cls.unicef_user, _ = Group.objects.get_or_create(name="UNICEF User")

        cls.org1 = OrganizationFactory(vendor_number="VN001", name="Test Org 1")
        cls.org2 = OrganizationFactory(vendor_number="VN002", name="Test Org 2")
        cls.org3 = OrganizationFactory(vendor_number="VN003", name="Test Org 3")

        cls._create_test_users()

    @classmethod
    def _create_test_users(cls):

        cls.user1 = UserFactory(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            realms__data=[],
            is_active=True,
        )
        cls.user1.profile.organization = cls.org1
        cls.user1.profile.save()

        Realm.objects.create(
            user=cls.user1,
            country=cls.test_country,
            organization=cls.org1,
            group=cls.ip_lm_editor,
            is_active=True,
        )

        cls.user2 = UserFactory(
            email="jane.smith@example.com",
            first_name="Jane",
            last_name="Smith",
            realms__data=[],
            is_active=True,
        )
        cls.user2.profile.organization = cls.org2
        cls.user2.profile.save()
        Realm.objects.create(
            user=cls.user2,
            country=cls.test_country,
            organization=cls.org2,
            group=cls.driver,
            is_active=True,
        )

        cls.user3 = UserFactory(
            email="bob.johnson@example.com",
            first_name="Bob",
            last_name="Johnson",
            realms__data=[],
            is_active=True,
        )
        cls.user3.profile.organization = cls.org3
        cls.user3.profile.save()
        Realm.objects.create(
            user=cls.user3,
            country=cls.test_country,
            organization=cls.org3,
            group=cls.driver,
            is_active=True,
        )
        Realm.objects.create(
            user=cls.user3,
            country=cls.test_country,
            organization=cls.org3,
            group=cls.ip_lm_editor,
            is_active=True,
        )

        cls.user4 = UserFactory(
            email="alice.admin@example.com",
            first_name="Alice",
            last_name="Admin",
            realms__data=[],
            is_active=True,
        )
        cls.user4.profile.organization = cls.org1
        cls.user4.profile.save()
        Realm.objects.create(
            user=cls.user4,
            country=cls.test_country,
            organization=cls.org1,
            group=cls.admin_role,
            is_active=True,
        )

        cls.user5_inactive = UserFactory(
            email="inactive.user@example.com",
            first_name="Inactive",
            last_name="User",
            realms__data=[],
            is_active=False,
        )
        cls.user5_inactive.profile.organization = cls.org2
        cls.user5_inactive.profile.save()
        cls.user5_inactive.refresh_from_db()
        Realm.objects.create(
            user=cls.user5_inactive,
            country=cls.test_country,
            organization=cls.org2,
            group=cls.driver,
            is_active=True,
        )

        cls.user6_inactive_realm = UserFactory(
            email="norealm.user@example.com",
            first_name="NoRealm",
            last_name="User",
            realms__data=[],
            is_active=True,
        )
        cls.user6_inactive_realm.profile.organization = cls.org1
        cls.user6_inactive_realm.profile.save()
        Realm.objects.create(
            user=cls.user6_inactive_realm,
            country=cls.test_country,
            organization=cls.org1,
            group=cls.driver,
            is_active=False,
        )

        cls.user7 = UserFactory(
            email="unicef.user@example.com",
            first_name="Unicef",
            last_name="Staff",
            realms__data=[],
            is_active=True,
        )
        cls.user7.profile.organization = cls.org2
        cls.user7.profile.save()
        Realm.objects.create(
            user=cls.user7,
            country=cls.test_country,
            organization=cls.org2,
            group=cls.unicef_user,
            is_active=True,
        )

    def test_unauthenticated_request_fails(self):
        response = self.client.get(self.url, {"workspace": "test", "role": "Driver"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_user_request_fails(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver"},
            user=self.unauthorized_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_workspace_filter_returns_400_error(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={"role": "Driver"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"], "Both 'workspace' and 'role' filters are required."
        )

    def test_missing_role_filter_returns_400_error(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={"workspace": "test"}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"], "Both 'workspace' and 'role' filters are required."
        )

    def test_missing_both_filters_returns_400_error(self):
        response = self.forced_auth_req(
            method="get", url=self.url, data={}, user=self.api_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_empty_filter_values_returns_400_error(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "", "role": ""},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_successful_request_with_valid_filters(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "IP LM Editor"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        emails = [u["email"] for u in response.data]
        self.assertIn("john.doe@example.com", emails)
        self.assertIn("bob.johnson@example.com", emails)
        self.assertNotIn("jane.smith@example.com", emails)

    def test_filter_by_driver_role(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("jane.smith@example.com", emails)
        self.assertIn("bob.johnson@example.com", emails)
        self.assertNotIn("john.doe@example.com", emails)

    def test_filter_workspace_partial_match(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "tes", "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("jane.smith@example.com", emails)

    def test_filter_role_partial_match(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Editor"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("john.doe@example.com", emails)
        self.assertIn("bob.johnson@example.com", emails)

    def test_case_insensitive_filter_matching(self):
        test_cases = [
            {"workspace": "test", "role": "driver"},
            {"workspace": "TEST", "role": "DRIVER"},
            {"workspace": "TeSt", "role": "DrIvEr"},
        ]

        for params in test_cases:
            response = self.forced_auth_req(
                method="get", url=self.url, data=params, user=self.api_user
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = (
                response.data.get("results", response.data)
                if isinstance(response.data, dict)
                else response.data
            )
            emails = [u["email"] for u in results]
            self.assertIn("jane.smith@example.com", emails)

    def test_filter_by_comma_separated_roles(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver,Admin"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertEqual(len(emails), 0)

    def test_filter_by_comma_separated_workspaces(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test,Uganda", "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertEqual(len(emails), 0)

    def test_filter_by_vendor_number_exact(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={
                "workspace": "test",
                "role": "IP LM Editor",
                "vendor_number": "VN001",
            },
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("john.doe@example.com", emails)
        self.assertNotIn("bob.johnson@example.com", emails)

    def test_filter_by_vendor_number_partial(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver", "vendor_number": "VN00"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("jane.smith@example.com", emails)
        self.assertIn("bob.johnson@example.com", emails)

    def test_search_by_email(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "IP LM Editor", "search": "john.doe"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["email"], "john.doe@example.com")

    def test_search_by_first_name(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver", "search": "Jane"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data
        emails = [u["email"] for u in results]
        self.assertIn("jane.smith@example.com", emails)

    def test_search_by_last_name(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver", "search": "Johnson"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data
        emails = [u["email"] for u in results]
        self.assertIn("bob.johnson@example.com", emails)

    def test_search_case_insensitive(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "IP LM Editor", "search": "JOHN"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertIn("john.doe@example.com", emails)

    def test_ordering_by_email_ascending(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver", "ordering": "email"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertEqual(emails, sorted(emails))

    def test_ordering_by_last_name_descending(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={
                "workspace": "test",
                "role": "Driver,IP LM Editor",
                "ordering": "-last_name",
            },
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        last_names = [u["last_name"] for u in response.data]
        self.assertEqual(last_names, sorted(last_names, reverse=True))

    def test_ordering_by_first_name_ascending(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={
                "workspace": "test",
                "role": "Driver,IP LM Editor",
                "ordering": "first_name",
            },
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_names = [u["first_name"] for u in response.data]
        self.assertEqual(first_names, sorted(first_names))

    def test_default_ordering_is_by_email(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver,IP LM Editor"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertEqual(emails, sorted(emails))

    def test_users_with_inactive_realms_not_matched(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        self.assertNotIn("norealm.user@example.com", emails)

    def test_empty_results_for_non_matching_filters(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "NonExistentCountry", "role": "NonExistentRole"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_user_with_multiple_roles_appears_once(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        emails = [u["email"] for u in response.data]
        bob_count = emails.count("bob.johnson@example.com")
        self.assertEqual(bob_count, 1)

    def test_response_includes_all_required_fields(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "IP LM Editor"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

        user_data = response.data[0]
        required_fields = ["id", "email", "first_name", "last_name", "vendor_number"]
        for field in required_fields:
            self.assertIn(field, user_data, f"Field '{field}' missing in response")

    def test_vendor_number_field_populated_correctly(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": "test", "role": "IP LM Editor"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user1_data = None
        for user in response.data:
            if user["email"] == "john.doe@example.com":
                user1_data = user
                break

        self.assertIsNotNone(user1_data)
        self.assertEqual(user1_data["vendor_number"], "VN001")

    def test_special_characters_in_filters_handled_safely(self):
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            '" OR "1"="1',
            "%",
            "_",
            "\\",
            "'",
            '"',
        ]

        for dangerous_input in dangerous_inputs:
            response = self.forced_auth_req(
                method="get",
                url=self.url,
                data={"workspace": dangerous_input, "role": dangerous_input},
                user=self.api_user,
            )
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )

    def test_very_long_filter_values_handled(self):
        long_string = "A" * 1000
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"workspace": long_string, "role": "Driver"},
            user=self.api_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestVisionLMSMExportItemAuditLog(BaseTenantTestCase):

    url = reverse("last_mile:vision-export-data")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tenant = TenantSwitchFactory(
            name="lmsm_item_audit_logs",
            active=True,
        )
        cls.tenant.countries.add(connection.tenant)
        cls.tenant.flush()

        ItemAuditConfigurationFactory()

        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Test Partner'))
        cls.poi = PointOfInterestFactory(partner_organizations=[cls.partner])

        cls.split_time = timezone.now()

        with freeze_time(cls.split_time - timedelta(days=2)):
            cls.old_transfer = TransferFactory(
                destination_point=cls.poi,
                partner_organization=cls.partner,
                unicef_release_order='URO-OLD-001'
            )
            cls.old_material = MaterialFactory(number='MAT-OLD-001')
            cls.old_item = ItemFactory(
                transfer=cls.old_transfer,
                material=cls.old_material,
                quantity=10
            )

        with freeze_time(cls.split_time + timedelta(days=1)):
            cls.new_transfer = TransferFactory(
                destination_point=cls.poi,
                partner_organization=cls.partner,
                unicef_release_order='URO-NEW-001'
            )
            cls.new_material = MaterialFactory(number='MAT-NEW-001')
            cls.new_item = ItemFactory(
                transfer=cls.new_transfer,
                material=cls.new_material,
                quantity=20
            )

    def _get_and_decode_streaming_response(self, response):
        content_bytes = b"".join(response.streaming_content)
        if not content_bytes:
            return None
        return json.loads(content_bytes.decode("utf-8"))

    def setUp(self):
        base_audit_ids = models.ItemAuditLog.objects.filter(
            item_id__in=[self.old_item.id, self.new_item.id],
            action=models.ItemAuditLog.ACTION_CREATE
        ).values_list('id', flat=True)
        models.ItemAuditLog.objects.exclude(id__in=base_audit_ids).delete()

    def test_export_item_audit_log_successful(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = self._get_and_decode_streaming_response(response)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        for item in data:
            self.assertIn('id', item)
            self.assertIn('created', item)
            self.assertIn('modified', item)
            self.assertIn('item_id', item)
            self.assertIn('action', item)
            self.assertIn('transfer_id', item)

    def test_export_item_audit_log_with_last_modified_filter(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={
                "type": "item_audit_log",
                "last_modified": self.split_time.isoformat()
            },
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        item_ids = [item['item_id'] for item in data]
        self.assertIn(self.new_item.id, item_ids)
        self.assertNotIn(self.old_item.id, item_ids)

    def test_export_item_audit_log_includes_all_action_types(self):

        self.old_item.quantity = 15
        self.old_item.save()

        self.new_item.hidden = True
        self.new_item.save()

        temp_item = ItemFactory(
            transfer=self.new_transfer,
            material=self.new_material,
            quantity=30
        )

        temp_item.delete()

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        actions = set(item['action'] for item in data)
        self.assertIn(models.ItemAuditLog.ACTION_CREATE, actions)
        self.assertIn(models.ItemAuditLog.ACTION_UPDATE, actions)
        self.assertIn(models.ItemAuditLog.ACTION_SOFT_DELETE, actions)
        self.assertIn(models.ItemAuditLog.ACTION_DELETE, actions)

    def test_export_item_audit_log_empty_result(self):
        future_time = (timezone.now() + timedelta(days=30)).isoformat()

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={
                "type": "item_audit_log",
                "last_modified": future_time
            },
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(data, [])

    def test_export_item_audit_log_ordering_by_id(self):
        items_and_ids = []
        for i in range(3):
            item = ItemFactory(
                transfer=self.new_transfer,
                material=self.new_material,
                quantity=50 + i
            )
            audit_log = models.ItemAuditLog.objects.filter(
                item_id=item.id,
                action=models.ItemAuditLog.ACTION_CREATE
            ).first()
            if audit_log:
                items_and_ids.append(audit_log.id)

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        ids = [item['id'] for item in data]
        self.assertEqual(ids, sorted(ids))

    def test_export_item_audit_log_bulk_operations(self):
        items = []
        for i in range(10):
            item = ItemFactory(
                transfer=self.new_transfer,
                material=self.new_material,
                quantity=1000 + i,
                batch_id=f'BULK-{i:03d}'
            )
            items.append(item)

        for i, item in enumerate(items):
            item.quantity = 2000 + i
            item.save()

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        self.assertGreaterEqual(len(data), 22)  # 10*2 + 2 original

        bulk_item_ids = [item.id for item in items]
        bulk_audit_logs = [d for d in data if d['item_id'] in bulk_item_ids]

        create_count = sum(1 for log in bulk_audit_logs if log['action'] == 'CREATE')
        update_count = sum(1 for log in bulk_audit_logs if log['action'] == 'UPDATE')

        self.assertEqual(create_count, 10)
        self.assertEqual(update_count, 10)

    def test_export_item_audit_log_with_null_transfer_info(self):
        models.ItemAuditLog.objects.create(
            item_id=99999,
            action=models.ItemAuditLog.ACTION_CREATE,
            transfer_info=None,
            changed_fields=[],
            old_values=None,
            new_values={'quantity': 100}
        )

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        null_transfer_logs = [d for d in data if d['item_id'] == 99999]
        self.assertEqual(len(null_transfer_logs), 1)
        self.assertIsNone(null_transfer_logs[0]['transfer_id'])

    def test_export_item_audit_log_permissions(self):
        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.unauthorized_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_item_audit_log_complex_scenario(self):
        transfer3 = TransferFactory(
            partner_organization=self.partner,
            unicef_release_order='URO-003'
        )

        item1 = ItemFactory(transfer=transfer3, material=self.new_material, quantity=100)
        item2 = ItemFactory(transfer=transfer3, material=self.old_material, quantity=200)

        for i in range(3):
            item1.quantity = 100 + (i + 1) * 10
            item1.save()

        item2.hidden = True
        item2.save()

        item3 = ItemFactory(transfer=transfer3, material=self.new_material, quantity=300)
        item3_id = item3.id
        item3.delete()

        response = self.forced_auth_req(
            method="get",
            url=self.url,
            data={"type": "item_audit_log"},
            user=self.api_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)

        item1_logs = [d for d in data if d['item_id'] == item1.id]
        item2_logs = [d for d in data if d['item_id'] == item2.id]
        item3_logs = [d for d in data if d['item_id'] == item3_id]

        self.assertEqual(len(item1_logs), 4)

        self.assertEqual(len(item2_logs), 2)

        self.assertEqual(len(item3_logs), 2)

        transfer3_logs = [d for d in data if d['item_id'] in [item1.id, item2.id, item3_id]]
        for log in transfer3_logs:
            self.assertEqual(log['transfer_id'], transfer3.id)
