from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import ItemFactory, TransferFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserPermissionFactory


class TestTransferHistoryViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory(name='Organization')
        cls.partner = PartnerFactory(organization=cls.organization)
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
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
        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_HISTORY_ADMIN_PANEL}-list')

    def test_get_transfer_history(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        transfer_2 = TransferFactory(unicef_release_order="Test Order#2", transfer_history_id=response.data.get('results')[0].get('id'))
        transfer_3 = TransferFactory(unicef_release_order="Test Order#3", transfer_history_id=response.data.get('results')[0].get('id'))
        ItemFactory(transfer=transfer_2, origin_transfer=self.transfer_1, batch_id="test_itm_2")
        ItemFactory(transfer=transfer_3, origin_transfer=self.transfer_1, batch_id="test_itm_3")

        response = self.forced_auth_req('get', reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_EVIDENCE_ADMIN_PANEL}-detail', kwargs={'transfer_history_id': response.data.get('results')[0].get('id')}), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['unicef_release_order'], transfer_3.unicef_release_order)
        self.assertEqual(response.data[1]['unicef_release_order'], transfer_2.unicef_release_order)
        self.assertEqual(response.data[2]['unicef_release_order'], self.transfer_1.unicef_release_order)

    def test_get_transfer_history_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req('get', reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_EVIDENCE_ADMIN_PANEL}-detail', kwargs={'transfer_history_id': 1}), user=self.simple_user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_transfer_history_incorect_permission(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req('get', reverse(f'{ADMIN_PANEL_APP_NAME}:{TRANSFER_EVIDENCE_ADMIN_PANEL}-detail', kwargs={'transfer_history_id': 1}), user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
