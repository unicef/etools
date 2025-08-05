import json
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.urls import reverse
from django.utils import timezone

from applications.last_mile.tests.factories import (
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
from etools.applications.last_mile import models
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestVisionIngestTransfersApiView(BaseTenantTestCase):
    url = reverse('last_mile:vision-ingest-transfers')

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.unicef_warehouse = PointOfInterestFactory(id=1, name="UNICEF Main Warehouse")

        cls.partner_org1 = OrganizationFactory(vendor_number='IP12345')
        cls.partner1 = PartnerFactory(organization=cls.partner_org1)

        cls.partner_org2 = OrganizationFactory(vendor_number='IP67890')
        cls.partner2 = PartnerFactory(organization=cls.partner_org2)

        cls.org_without_partner = OrganizationFactory(vendor_number='NO_PARTNER_PROFILE')

        cls.material1 = MaterialFactory(number='MAT-001', short_description="Biscuits")
        cls.material2 = MaterialFactory(number='MAT-002', short_description="Water Tablets")

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
                "PurchaseOrderType": "null"
            }
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.unauthorized_user)
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
            }
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

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
        existing_transfer = TransferFactory(unicef_release_order="RO-EXISTING", partner_organization=self.partner1)
        self.assertEqual(models.Transfer.objects.count(), 1)

        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-EXISTING",
            "ImplementingPartner": "IP12345",
            "ItemDescription": "This item will be ignored",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "30",
            "UOM": "EA",
            "Quantity": 50,
            "BatchNumber": "B3",
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(existing_transfer.items.count(), 1)
        self.assertEqual(models.Item.objects.first().unicef_ro_item, "30")

    def test_ingest_skips_row_if_partner_not_found(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-FAIL",
            "ImplementingPartner": "IP_DOES_NOT_EXIST",
            "MaterialNumber": "MAT-001",
            "ItemDescription": "This item will be ignored",
            "ReleaseOrderItem": "10",
            "UOM": "EA",
            "Quantity": 10,
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_ingest_skips_row_if_organization_has_no_partner_profile(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-FAIL",
            "ImplementingPartner": "NO_PARTNER_PROFILE",
            "MaterialNumber": "MAT-001",
            "ItemDescription": "This item will be ignored",
            "ReleaseOrderItem": "10",
            "UOM": "EA",
            "Quantity": 10,
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

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
            }
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(models.Item.objects.first().material, self.material1)

    def test_idempotency_duplicate_payload_does_not_create_new_objects(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-IDEMPOTENT",
            "ImplementingPartner": "IP12345",
            "ItemDescription": "This item will be ignored",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "Quantity": 10,
            "UOM": "EA",
            "BatchNumber": "B1",
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

    def test_rows_with_incorrect_event_are_ignored(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-GOOD", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "ItemDescription": "This item will be ignored", "UOM": "EA"},
            {"Event": "AR", "ReleaseOrder": "RO-BAD", "ImplementingPartner": "IP67890", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 20, "BatchNumber": "B2", "ItemDescription": "This item will be ignored", "UOM": "EA"},
            {"Event": "OTHER", "ReleaseOrder": "RO-BAD", "ImplementingPartner": "IP67890", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "30", "Quantity": 30, "BatchNumber": "B3", "ItemDescription": "This item will be ignored", "UOM": "EA"}
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)
        self.assertEqual(models.Transfer.objects.first().unicef_release_order, "RO-GOOD")

    def test_html_tags_are_stripped_and_other_fields_are_saved(self):
        payload = [{
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
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        transfer = models.Transfer.objects.first()
        self.assertEqual(transfer.purchase_order_id, "PO-CLEAN")

        item = models.Item.objects.first()

        self.assertIsNotNone(item.expiry_date)

        self.assertEqual(item.other['HandoverNumber'], 'HO-123')
        self.assertEqual(item.other['Plant'], 'PL-01')
        self.assertEqual(item.other['itemid'], 'RO-CLEAN-10')

    def test_item_without_batch_id_gets_defaults(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-NOBATCH",
            "ImplementingPartner": "IP12345",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "ItemDescription": "This item will be ignored",
            "Quantity": 15,
            "UOM": "EA"
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = models.Item.objects.first()
        self.assertEqual(item.quantity, 15)
        self.assertEqual(item.uom, "EA")
        self.assertEqual(item.conversion_factor, 1.0)

    def test_permission_denied_for_authenticated_non_api_user(self):
        regular_user = UserFactory()

        payload = [{"Event": "LD", "ReleaseOrder": "RO-DENIED", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001"}]

        response = self.forced_auth_req(
            'post', self.url, user=regular_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(models.Transfer.objects.count(), 0)

    def test_graceful_handling_of_empty_payload(self):
        payload = []

        response = self.forced_auth_req(
            'post', self.url, user=self.api_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_graceful_handling_of_fully_invalid_payload(self):
        payload = [
            {"Event": "AR", "ReleaseOrder": "RO-BAD-1", "ImplementingPartner": "IP12345"},
            {"Event": "XX", "ReleaseOrder": "RO-BAD-2", "ImplementingPartner": "IP12345"},
        ]

        response = self.forced_auth_req(
            'post', self.url, user=self.api_user, data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_uom_is_popped_when_matching_material_original_uom(self):
        self.material1.original_uom = "BOX"
        self.material1.uom = "EA"
        self.material1.save()

        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-UOM-TEST",
            "ImplementingPartner": "IP12345",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "Quantity": 50,
            "ItemDescription": "This item will be ignored",
            "UOM": "BOX",
            "BatchNumber": "B-UOM",
        }]

        response = self.forced_auth_req(
            'post', self.url, user=self.api_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = models.Item.objects.first()
        self.assertEqual(item.uom, None)

    def test_robustness_with_numeric_fields_as_strings(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-STRING-NUM",
            "ImplementingPartner": "IP12345",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "Quantity": "150",
            "AmountUSD": "350.55",
            "BatchNumber": "B1",
            "ItemDescription": "This item will be ignored",
            "UOM": "EA"
        }]

        response = self.forced_auth_req(
            'post', self.url, user=self.api_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = models.Item.objects.first()
        self.assertEqual(item.quantity, 150)
        self.assertEqual(item.amount_usd, Decimal("350.55"))

    def test_validation_error_on_missing_required_field(self):
        payload = [{
            # "ReleaseOrder": "RO-MISSING",  <-- Missing required field
            "Event": "LD",
            "ImplementingPartner": "IP12345",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "Quantity": 10,
            "BatchNumber": "B1",
            "UOM": "EA",
            "ItemDescription": "description"
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ReleaseOrder', response.data[0])
        self.assertEqual(response.data[0]['ReleaseOrder'][0].code, 'required')
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

    def test_validation_error_on_malformed_data(self):
        payload = [{
            "Event": "LD",
            "ReleaseOrder": "RO-BAD-DATA",
            "ImplementingPartner": "IP12345",
            "MaterialNumber": "MAT-001",
            "ReleaseOrderItem": "10",
            "Quantity": "this-is-not-a-number",
            "BatchNumber": "B1",
            "UOM": "EA",
            "ItemDescription": "description"
        }]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Quantity', response.data[0])
        self.assertEqual(response.data[0]['Quantity'][0].code, 'invalid')
        self.assertEqual(models.Item.objects.count(), 0)

    def test_response_structure_on_full_success(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-A1", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 100, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-A1", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 200, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_response = {
            "status": "Completed",
            "transfers_created": 1,
            "items_created": 2,
            "skipped_count": 0,
            "details": {
                "skipped_transfers": [],
                "skipped_items": []
            }
        }
        self.assertEqual(response.data, expected_response)

    def test_partial_ingest_with_skipped_items_reported_in_response(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-PARTIAL", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 100, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-PARTIAL", "ImplementingPartner": "IP12345", "MaterialNumber": "INVALID-MATERIAL", "ReleaseOrderItem": "20", "Quantity": 200, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data['transfers_created'], 1)
        self.assertEqual(response.data['items_created'], 1)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(len(response.data['details']['skipped_items']), 1)

        skipped_report = response.data['details']['skipped_items'][0]
        self.assertEqual(skipped_report['reason'], "Material number 'INVALID-MATERIAL' not found.")
        self.assertEqual(skipped_report['item']['material_number'], 'INVALID-MATERIAL')

    def test_idempotency_reports_skipped_items_on_second_run(self):
        payload = [{"Event": "LD", "ReleaseOrder": "RO-IDEMPOTENT", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"}]

        first_response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data['items_created'], 1)
        self.assertEqual(first_response.data['skipped_count'], 0)
        self.assertEqual(models.Item.objects.count(), 1)

        second_response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(second_response.data['items_created'], 0)
        self.assertEqual(second_response.data['skipped_count'], 1)
        self.assertEqual(len(second_response.data['details']['skipped_items']), 1)
        self.assertEqual(second_response.data['details']['skipped_items'][0]['reason'], "Duplicate item found in database.")

    def test_multiple_new_transfers_in_one_payload(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-MULTI-1", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-MULTI-2", "ImplementingPartner": "IP67890", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "10", "Quantity": 20, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 2)

        self.assertEqual(response.data['transfers_created'], 2)
        self.assertEqual(response.data['items_created'], 2)
        self.assertEqual(response.data['skipped_count'], 0)

    def test_duplicate_item_within_payload_is_skipped_and_reported(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-DUP-ITEM", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 100, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-DUP-ITEM", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "10", "Quantity": 200, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data['items_created'], 1)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(len(response.data['details']['skipped_items']), 1)

        skipped_report = response.data['details']['skipped_items'][0]
        self.assertEqual(skipped_report['reason'], "Duplicate item found within the same payload.")
        self.assertEqual(skipped_report['item']['unicef_ro_item'], '10')

    def test_payload_with_conflicting_partners_for_same_release_order(self):
        """
        Tests that if a payload contains conflicting ImplementingPartners for the same
        ReleaseOrder, the system creates only ONE transfer using the first partner it
        encounters and adds all items to it.
        """
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-CONFLICT", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-CONFLICT", "ImplementingPartner": "IP67890", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 20, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(models.Item.objects.count(), 2)

        transfer = models.Transfer.objects.first()
        self.assertEqual(transfer.partner_organization, self.partner1)
        self.assertEqual(transfer.items.count(), 2)

        self.assertEqual(response.data['transfers_created'], 1)
        self.assertEqual(response.data['items_created'], 2)
        self.assertEqual(response.data['skipped_count'], 0)

    def test_all_transfers_fail_no_items_are_created(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-FAIL-1", "ImplementingPartner": "BAD_IP_1", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-FAIL-2", "ImplementingPartner": "BAD_IP_2", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 20, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(models.Item.objects.count(), 0)

        self.assertEqual(response.data['transfers_created'], 0)
        self.assertEqual(response.data['items_created'], 0)
        self.assertEqual(response.data['skipped_count'], 2)
        self.assertEqual(len(response.data['details']['skipped_transfers']), 2)
        self.assertEqual(len(response.data['details']['skipped_items']), 0)
        self.assertIn("RO-FAIL-1", str(response.data['details']['skipped_transfers']))
        self.assertIn("RO-FAIL-2", str(response.data['details']['skipped_transfers']))

    def test_graceful_handling_of_payload_with_no_ld_events(self):
        payload = [
            {"Event": "AR", "ReleaseOrder": "RO-IGNORE-1", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "GR", "ReleaseOrder": "RO-IGNORE-2", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 20, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 0)
        self.assertEqual(response.data['detail'], "No rows with Event 'LD' found in the payload.")

    def test_create_transfer_with_items_wrong_uom(self):
        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-IGNORE-1", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "CAAR", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-IGNORE-2", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "20", "Quantity": 20, "BatchNumber": "B2", "UOM": "CAR", "ItemDescription": "d"},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 1)

        self.assertEqual(response.data['transfers_created'], 2)
        self.assertEqual(response.data['items_created'], 1)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['details']['skipped_items'][0]['reason'], "UOM 'CAAR' not valid.")

    def test_mixed_payload_creates_new_and_adds_to_existing_transfer(self):
        existing_transfer = TransferFactory(unicef_release_order="RO-EXISTING", partner_organization=self.partner1)
        self.assertEqual(models.Transfer.objects.count(), 1)

        payload = [
            {"Event": "LD", "ReleaseOrder": "RO-EXISTING", "ImplementingPartner": "IP12345", "MaterialNumber": "MAT-001", "ReleaseOrderItem": "10", "Quantity": 10, "BatchNumber": "B1", "UOM": "EA", "ItemDescription": "d"},
            {"Event": "LD", "ReleaseOrder": "RO-NEW", "ImplementingPartner": "IP67890", "MaterialNumber": "MAT-002", "ReleaseOrderItem": "10", "Quantity": 20, "BatchNumber": "B2", "UOM": "EA", "ItemDescription": "d"},
        ]

        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Transfer.objects.count(), 2)
        self.assertEqual(models.Item.objects.count(), 2)

        self.assertEqual(response.data['transfers_created'], 1)
        self.assertEqual(response.data['items_created'], 2)
        self.assertEqual(response.data['skipped_count'], 0)

        self.assertEqual(existing_transfer.items.count(), 1)
        new_transfer = models.Transfer.objects.get(unicef_release_order="RO-NEW")
        self.assertEqual(new_transfer.items.count(), 1)
        self.assertEqual(new_transfer.partner_organization, self.partner2)


class TestVisionIngestMaterialsApiView(BaseTenantTestCase):

    url = reverse('last_mile:vision-ingest-materials')

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.api_user = UserFactory(is_superuser=True)
        cls.unauthorized_user = UserFactory(is_superuser=False)

        cls.existing_material = MaterialFactory(
            number='EXISTING-MAT-001',
            short_description='An already existing material'
        )

    def test_permission_denied_for_non_api_user(self):
        payload = [{'MaterialNumber': 'NEW-MAT-001'}]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.unauthorized_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(models.Material.objects.filter(number='NEW-MAT-001').exists())

    def test_other_http_methods_are_disallowed(self):
        self.client.force_authenticate(self.api_user)
        response_get = self.client.get(self.url)
        self.assertEqual(response_get.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response_put = self.client.put(self.url, data={}, format='json')
        self.assertEqual(response_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_successful_ingest_creates_materials(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "MAT-A1", "ShortDescription": "Material A1"},
            {"MaterialNumber": "MAT-B2", "ShortDescription": "Material B2"},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 2)

        response_data = response.data
        self.assertEqual(response_data['created_count'], 2)
        self.assertEqual(response_data['skipped_count'], 0)
        self.assertEqual(len(response_data['details']['skipped_existing_in_db']), 0)
        self.assertEqual(len(response_data['details']['skipped_duplicate_in_payload']), 0)

        self.assertTrue(models.Material.objects.filter(number="MAT-A1", short_description="Material A1").exists())

    def test_idempotency_existing_material_is_skipped(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": self.existing_material.number, "ShortDescription": "Updated but should be ignored"},
            {"MaterialNumber": "MAT-NEW-IDEMPOTENT", "ShortDescription": "A new material"},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 1)

        response_data = response.data
        self.assertEqual(response_data['created_count'], 1)
        self.assertEqual(response_data['skipped_count'], 1)
        self.assertIn(self.existing_material.number, response_data['details']['skipped_existing_in_db'])

        self.existing_material.refresh_from_db()
        self.assertEqual(self.existing_material.short_description, 'An already existing material')

    def test_ingest_handles_duplicates_within_payload(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "DUP-IN-PAYLOAD", "ShortDescription": "First instance"},
            {"MaterialNumber": "MAT-UNIQUE", "ShortDescription": "Another material"},
            {"MaterialNumber": "DUP-IN-PAYLOAD", "ShortDescription": "Second instance (should be ignored)"},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 2)

        response_data = response.data
        self.assertEqual(response_data['created_count'], 2)
        self.assertEqual(response_data['skipped_count'], 1)
        self.assertIn("DUP-IN-PAYLOAD", response_data['details']['skipped_duplicate_in_payload'])

    def test_ingest_with_mixed_payload_of_new_and_duplicates(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "NEW-MAT-1"},
            {"MaterialNumber": self.existing_material.number},
            {"MaterialNumber": "DUP-MAT-1"},
            {"MaterialNumber": "NEW-MAT-2"},
            {"MaterialNumber": "DUP-MAT-1"},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count + 3)

        response_data = response.data
        self.assertEqual(response_data['created_count'], 3)
        self.assertEqual(response_data['skipped_count'], 2)
        self.assertEqual(response_data['details']['skipped_existing_in_db'], [self.existing_material.number])
        self.assertEqual(response_data['details']['skipped_duplicate_in_payload'], ["DUP-MAT-1"])

    def test_html_tags_are_stripped_from_fields(self):
        payload = [{"MaterialNumber": "MAT-CLEAN", "ShortDescription": "<b>Bold</b>"}]
        self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        material = models.Material.objects.get(number="MAT-CLEAN")
        self.assertEqual(material.short_description, "Bold")

    def test_ingest_fails_if_any_item_is_missing_material_number(self):
        initial_count = models.Material.objects.count()
        payload = [
            {"MaterialNumber": "MAT-VALID-1"},
            {"ShortDescription": "This item is missing the material number."},
        ]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.data
        self.assertIsInstance(response_data, list)
        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[1], {'MaterialNumber': ['This field is required.']})
        self.assertEqual(models.Material.objects.count(), initial_count)

    def test_graceful_handling_of_empty_payload(self):
        initial_count = models.Material.objects.count()
        response = self.forced_auth_req(method="post", url=self.url, data=[], user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Material.objects.count(), initial_count)

        response_data = response.data
        self.assertEqual(response_data['created_count'], 0)
        self.assertEqual(response_data['skipped_count'], 0)

    def test_invalid_payload_format_not_a_list_fails(self):
        payload = {"MaterialNumber": "MAT-FAIL"}
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Expected a list of items but got type", str(response.data))

    def test_invalid_payload_format_list_with_non_dict_fails(self):
        payload = [{"MaterialNumber": "MAT-OK"}, "i-am-not-a-dict"]
        response = self.forced_auth_req(method="post", url=self.url, data=payload, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid data. Expected a dictionary, but got str", str(response.data[1]))


class TestVisionLMSMExport(BaseTenantTestCase):
    url = reverse('last_mile:vision-export-data')

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
        return json.loads(content_bytes.decode('utf-8'))

    def test_permission_denied_for_non_api_user(self):
        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'transfer'}, user=self.unauthorized_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_http_methods_are_disallowed(self):
        self.client.force_authenticate(self.api_user)
        response_post = self.client.post(self.url, data={'type': 'transfer'})
        self.assertEqual(response_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_request_fails_if_type_param_is_missing(self):
        response = self.forced_auth_req(method="get", url=self.url, data={}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'type': 'This field is required.'})

    def test_request_fails_if_type_param_is_invalid(self):
        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'invalid_model'}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'type': "'invalid_model' is not a valid data model type."})

    def test_request_fails_for_invalid_last_modified_format(self):
        params = {'type': 'transfer', 'last_modified': 'not-a-valid-date'}
        response = self.forced_auth_req(method="get", url=self.url, data=params, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'last_modified': "Invalid ISO 8601 format for 'last_modified'."})

    def test_export_all_transfers(self):
        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'transfer'}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), models.Transfer.objects.count())
        self.assertEqual(len(data), 8)

    def test_export_all_pois(self):
        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'poi'}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), models.PointOfInterest.all_objects.count())
        self.assertEqual(len(data), 18)

    def test_export_all_items(self):
        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'item'}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), models.Item.objects.count())
        self.assertEqual(len(data), 4)

    def test_export_filtered_transfers_by_last_modified(self):
        params = {'type': 'transfer', 'last_modified': self.split_time.isoformat()}
        response = self.forced_auth_req(method="get", url=self.url, data=params, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 4)

    def test_export_filtered_pois_by_last_modified(self):
        params = {'type': 'poi', 'last_modified': self.split_time.isoformat()}
        response = self.forced_auth_req(method="get", url=self.url, data=params, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 9)

    def test_export_filtered_items_by_last_modified(self):
        params = {'type': 'item', 'last_modified': self.split_time.isoformat()}
        response = self.forced_auth_req(method="get", url=self.url, data=params, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], self.new_item.id)

    def test_export_returns_empty_list_for_filter_with_no_results(self):
        future_time = (timezone.now() + timedelta(days=30)).isoformat()
        params = {'type': 'item', 'last_modified': future_time}
        response = self.forced_auth_req(method="get", url=self.url, data=params, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(data, [])

    def test_export_returns_empty_list_for_model_with_no_data(self):
        models.Transfer.objects.all().delete()
        self.assertEqual(models.Transfer.objects.count(), 0)

        response = self.forced_auth_req(method="get", url=self.url, data={'type': 'transfer'}, user=self.api_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_and_decode_streaming_response(response)
        self.assertEqual(data, [])
