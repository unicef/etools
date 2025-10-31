from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import Item, Transfer
from etools.applications.last_mile.tests.factories import ItemFactory, TransferFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserPermissionFactory


class TestRevertTransfersViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory(name='Organization')
        cls.partner = PartnerFactory(organization=cls.organization)
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
            profile__organization=cls.partner.organization,
            perms=[TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.transfer_1 = TransferFactory(unicef_release_order="Test Order#1")
        cls.item_1 = ItemFactory(transfer=cls.transfer_1, batch_id="test_itm_1")
        cls.simple_user = SimpleUserFactory()

    def test_get_transfer_details_success(self):
        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-details', kwargs={'pk': self.transfer_1.id})
        with self.assertNumQueries(9):
            response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.transfer_1.id)
        self.assertEqual(response.data['unicef_release_order'], self.transfer_1.unicef_release_order)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['batch_id'], self.item_1.batch_id)

    def test_get_transfer_details_forbidden(self):
        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-details', kwargs={'pk': self.transfer_1.id})
        response = self.forced_auth_req('get', url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req('get', url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reverse_transfer_success(self):
        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': self.transfer_1.id})
        old_transfer_item_count = self.transfer_1.items.count()
        old_destination = self.transfer_1.destination_point
        old_origin = self.transfer_1.origin_point

        self.assertEqual(old_transfer_item_count, 1)

        with self.assertNumQueries(13):
            response = self.forced_auth_req('put', url, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.transfer_1.refresh_from_db()
        self.assertEqual(self.transfer_1.items.count(), 0, "Original transfer should have no items after reversal")

        new_transfer_id = response.data.get('id')
        new_transfer = Transfer.objects.get(id=new_transfer_id)
        self.assertEqual(new_transfer.origin_transfer, self.transfer_1)
        self.assertTrue(new_transfer.unicef_release_order.endswith('_reversed'))
        self.assertEqual(new_transfer.destination_point, old_origin)
        self.assertEqual(new_transfer.origin_point, old_destination)
        self.assertEqual(new_transfer.items.count(), old_transfer_item_count)

        self.item_1.refresh_from_db()
        self.assertEqual(self.item_1.transfer, new_transfer, "Item should be associated with the new transfer")

    def test_reverse_transfer_forbidden(self):
        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': self.transfer_1.id})
        response = self.forced_auth_req('put', url, user=self.simple_user, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req('put', url, user=self.partner_staff_without_correct_permissions, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_actions_on_non_existent_transfer(self):
        non_existent_pk = 99999
        url_details = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-details', kwargs={'pk': non_existent_pk})
        response = self.forced_auth_req('get', url_details, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        url_reverse = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': non_existent_pk})
        response = self.forced_auth_req('put', url_reverse, user=self.partner_staff, data={})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reverse_transfer_validation_errors_and_atomicity(self):
        transfer_no_items = TransferFactory()
        url_no_items = reverse(
            f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_no_items.id}
        )
        response = self.forced_auth_req('put', url_no_items, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("transfer_has_no_items", str(response.data))
        transfer_no_items.refresh_from_db()
        self.assertEqual(transfer_no_items.items.count(), 0)

        transfer_handover = TransferFactory(transfer_type=Transfer.HANDOVER)
        ItemFactory(transfer=transfer_handover)
        url_handover = reverse(
            f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_handover.id}
        )
        response = self.forced_auth_req('put', url_handover, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("transfer_type_handover_not_allowed", str(response.data))
        transfer_handover.refresh_from_db()
        self.assertEqual(transfer_handover.items.count(), 1)
        self.assertEqual(transfer_handover.transfer_type, Transfer.HANDOVER)

    def test_reverse_transfer_ignores_request_body(self):
        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': self.transfer_1.id})
        payload = {'unicef_release_order': 'This should be ignored'}
        response = self.forced_auth_req('put', url, user=self.partner_staff, data=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_transfer = Transfer.objects.get(id=response.data['id'])
        self.assertNotEqual(new_transfer.unicef_release_order, payload['unicef_release_order'])
        self.assertTrue(new_transfer.unicef_release_order.startswith(self.transfer_1.unicef_release_order))
        self.assertTrue(new_transfer.unicef_release_order.endswith('_reversed'))

    def test_reverse_transfer_with_multiple_items(self):
        transfer_multi_item = TransferFactory()
        item1 = ItemFactory(transfer=transfer_multi_item)
        item2 = ItemFactory(transfer=transfer_multi_item)
        self.assertEqual(transfer_multi_item.items.count(), 2)

        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_multi_item.id})
        response = self.forced_auth_req('put', url, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transfer_multi_item.refresh_from_db()
        self.assertEqual(transfer_multi_item.items.count(), 0)

        new_transfer = Transfer.objects.get(id=response.data['id'])
        self.assertEqual(new_transfer.items.count(), 2)
        self.assertIn(item1, new_transfer.items.all())
        self.assertIn(item2, new_transfer.items.all())

    def test_reverse_transfer_copies_all_relevant_fields(self):
        transfer_detailed = TransferFactory(
            reason="Logistical issue",
            comment="Driver unavailable",
            purchase_order_id=123,
            waybill_id=456,
            pd_number="PD/2023/789"
        )
        ItemFactory(transfer=transfer_detailed)

        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_detailed.id})
        response = self.forced_auth_req('put', url, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_transfer = Transfer.objects.get(id=response.data['id'])

        self.assertEqual(new_transfer.reason, transfer_detailed.reason)
        self.assertEqual(new_transfer.comment, transfer_detailed.comment)
        self.assertEqual(new_transfer.purchase_order_id, str(transfer_detailed.purchase_order_id))
        self.assertEqual(new_transfer.waybill_id, str(transfer_detailed.waybill_id))
        self.assertEqual(new_transfer.pd_number, transfer_detailed.pd_number)
        self.assertEqual(new_transfer.transfer_history, transfer_detailed.transfer_history)

    def test_unicef_release_order_truncation_on_reverse(self):
        long_order = "x" * 249
        self.assertEqual(len(long_order), 249)
        transfer_long_order = TransferFactory(unicef_release_order=long_order)
        ItemFactory(transfer=transfer_long_order)

        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_long_order.id})
        response = self.forced_auth_req('put', url, user=self.partner_staff, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_transfer = Transfer.objects.get(id=response.data['id'])
        expected_order = f"{long_order}_reversed"[:254]
        self.assertEqual(new_transfer.unicef_release_order, expected_order)
        self.assertEqual(len(new_transfer.unicef_release_order), 254)

    def test_reverse_a_previously_reversed_transfer(self):

        url_first_reverse = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': self.transfer_1.id})
        response1 = self.forced_auth_req('put', url_first_reverse, user=self.partner_staff, data={})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        reversed_transfer_1 = Transfer.objects.get(id=response1.data['id'])

        url_second_reverse = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': reversed_transfer_1.id})
        response2 = self.forced_auth_req('put', url_second_reverse, user=self.partner_staff, data={})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        reversed_transfer_2 = Transfer.objects.get(id=response2.data['id'])
        self.assertEqual(reversed_transfer_2.origin_transfer, reversed_transfer_1)
        self.assertEqual(reversed_transfer_2.origin_point, self.transfer_1.origin_point)
        self.assertEqual(reversed_transfer_2.destination_point, self.transfer_1.destination_point)
        self.item_1.refresh_from_db()
        self.assertEqual(self.item_1.transfer, reversed_transfer_2)
        self.assertTrue(reversed_transfer_2.unicef_release_order.endswith('_reversed'))
        self.assertTrue('_reversed_reversed' in reversed_transfer_2.unicef_release_order)

    def test_reverse_transfer_with_hidden_items(self):
        transfer_with_deleted_items = TransferFactory()
        active_item = ItemFactory(transfer=transfer_with_deleted_items)
        soft_deleted_item = ItemFactory(transfer=transfer_with_deleted_items)

        soft_deleted_item.is_hidden = True
        soft_deleted_item.save()
        soft_deleted_item.refresh_from_db()

        self.assertEqual(Item.all_objects.filter(transfer=transfer_with_deleted_items).count(), 2)

        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_with_deleted_items.id})
        response = self.forced_auth_req('put', url, user=self.partner_staff, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_transfer = Transfer.objects.get(id=response.data['id'])
        self.assertEqual(Item.all_objects.filter(transfer=new_transfer).count(), 2)

        active_item.refresh_from_db()
        soft_deleted_item.refresh_from_db()
        self.assertEqual(active_item.transfer, new_transfer)
        self.assertEqual(soft_deleted_item.transfer, new_transfer)

    def test_reverse_transfer_with_null_origin_destination(self):
        transfer_null_points = TransferFactory(origin_point=None)
        ItemFactory(transfer=transfer_null_points)
        old_destination = transfer_null_points.destination_point

        url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_REVERSE_ADMIN_PANEL}-reverse', kwargs={'pk': transfer_null_points.id})
        response = self.forced_auth_req('put', url, user=self.partner_staff, data={})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_transfer = Transfer.objects.get(id=response.data['id'])
        self.assertIsNone(new_transfer.destination_point)
        self.assertEqual(new_transfer.origin_point, old_destination)
