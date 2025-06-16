from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.util_scripts import set_country as real_set_country
from etools.applications.last_mile import models
from etools.applications.last_mile.tests.factories import MaterialFactory, PointOfInterestFactory, TransferFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory

PATH_TO_PATCH = 'etools.applications.last_mile.views_ext.set_country'


class VisionIngestTransfersApiViewTest(BaseTenantTestCase):
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

    def setUp(self):
        super().setUp()

        patcher = patch(PATH_TO_PATCH)

        self.mock_set_country = patcher.start()

        self.mock_set_country.side_effect = lambda _: real_set_country('test')

        self.addCleanup(patcher.stop)

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
            "UOM": "SHOULD BE IGNORED"
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
            "UOM": "SHOULD BE IGNORED"
        }]

        response = self.forced_auth_req(
            'post', self.url, user=self.api_user, data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = models.Item.objects.first()
        self.assertEqual(item.quantity, 150)
        self.assertEqual(item.amount_usd, Decimal("350.55"))
