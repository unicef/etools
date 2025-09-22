import datetime
from unittest import skip
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from rest_framework import status
from rest_framework.reverse import reverse
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.serializers import PointOfInterestNotificationSerializer
from etools.applications.last_mile.tests.factories import (
    ItemFactory,
    MaterialFactory,
    PartnerMaterialFactory,
    PointOfInterestFactory,
    TransferFactory,
)
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import AgreementFactory, PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestPointOfInterestTypeView(BaseTenantTestCase):
    fixtures = ('poi_type.json',)
    url = reverse('last_mile:poi-types-list')

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )

    def test_api_poi_types_list(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)


class TestHandoverPartnersListView(BaseTenantTestCase):
    url = reverse('last_mile:partners-list')

    @classmethod
    def setUp(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.hidden_partner = PartnerFactory(organization=OrganizationFactory(name='Hidden Partner'), hidden=True)
        cls.agreement_partner_draft = PartnerFactory(organization=OrganizationFactory(name='Agreement Partner Draft'))
        cls.agreement_draft = AgreementFactory(partner=cls.agreement_partner_draft, status='draft')
        cls.agreement_partner_signed = PartnerFactory(organization=OrganizationFactory(name='Agreement Partner Signed'))
        cls.agreement_signed = AgreementFactory(partner=cls.agreement_partner_signed, status='signed')
        cls.agreement_partner_ended = PartnerFactory(organization=OrganizationFactory(name='Agreement Partner Ended'))
        cls.agreement_ended = AgreementFactory(partner=cls.agreement_partner_ended, status='ended')
        cls.agreement_partner_suspended = PartnerFactory(organization=OrganizationFactory(name='Agreement Partner Suspended'))
        cls.agreement_suspended = AgreementFactory(partner=cls.agreement_partner_suspended, status='suspended')
        cls.agreement_partner_terminated = PartnerFactory(organization=OrganizationFactory(name='Agreement Partner Terminated'))
        cls.agreement_terminated = AgreementFactory(partner=cls.agreement_partner_terminated, status='terminated')
        cls.partner_without_name = PartnerFactory(organization=OrganizationFactory(name=''))
        cls.partner_is_deleted_flag = PartnerFactory(organization=OrganizationFactory(name='Deleted Partner'), deleted_flag=True)
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )

    def test_api_handover_partners_list(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 6)


class TestPointOfInterestView(BaseTenantTestCase):
    fixtures = ('poi_type.json',)

    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        # poi_type_id=4 -> school
        cls.poi_partner = PointOfInterestFactory(partner_organizations=[cls.partner], private=True, poi_type_id=4)

    def test_poi_list(self):
        url = reverse("last_mile:pois-list")
        PointOfInterestFactory(private=True)

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.poi_partner.pk, response.data['results'][0]['id'])

    def test_poi_list_type_filter(self):
        url = reverse("last_mile:pois-list")

        warehouse = PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=1)  # warehouse
        PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=2)  # distribution_point
        PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=3)  # hospital

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

        response = self.forced_auth_req('get', url, user=self.partner_staff, data={"poi_type": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(warehouse.pk, response.data['results'][0]['id'])

    def test_poi_list_selected_reason_filter(self):
        url = reverse("last_mile:pois-list")

        warehouse = PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=1)  # warehouse
        PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=2)  # distribution_point
        PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=3)  # hospital

        with self.assertNumQueries(3):
            response = self.forced_auth_req('get', url, user=self.partner_staff, data={"selected_reason": "DELIVERY"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(warehouse.pk, response.data['results'][0]['id'])

        response = self.forced_auth_req('get', url, user=self.partner_staff, data={"selected_reason": "DISTRIBUTION"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(
            ['distribution_point', 'hospital', 'school'],
            sorted([poi['poi_type']['category'] for poi in response.data['results']]))

    def test_item_list(self):
        url = reverse('last_mile:inventory-item-list', args=(self.poi_partner.pk,))
        transfer = TransferFactory(
            status=models.Transfer.COMPLETED, destination_point=self.poi_partner, partner_organization=self.partner)
        for i in range(5):
            ItemFactory(transfer=transfer)

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_upload_waybill(self):
        url = reverse('last_mile:pois-upload-waybill', args=(self.poi_partner.pk,))
        attachment = AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!'))
        recipient_1 = UserFactory(realms__data=['Waybill Recipient'])
        recipient_2 = UserFactory(realms__data=['Waybill Recipient'])

        self.assertEqual(models.Transfer.objects.count(), 0)
        mock_send = Mock()
        with patch("etools.applications.last_mile.tasks.send_notification_with_template", mock_send):
            response = self.forced_auth_req('post', url, user=self.partner_staff, data={'waybill_file': attachment.id})

        self.assertEqual(mock_send.call_count, 1)

        self.assertEqual(
            sorted(mock_send.call_args.kwargs['recipients']), sorted([recipient_1.email, recipient_2.email])
        )
        self.assertEqual(mock_send.call_args.kwargs['context']['waybill_url'], f'http://testserver{attachment.url}')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(models.Transfer.objects.count(), 0)


class TestInventoryItemListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.poi_partner = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)

    def test_api_item_list(self):
        url = reverse('last_mile:inventory-item-list', args=(self.poi_partner.pk,))
        transfer = TransferFactory(
            status=models.Transfer.COMPLETED, destination_point=self.poi_partner, partner_organization=self.partner
        )
        for i in range(5):
            ItemFactory(transfer=transfer)

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)


class TestTransferView(BaseTenantTestCase):
    fixtures = ('poi_type.json',)

    @classmethod
    def setUp(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_receive_handover = PartnerFactory(organization=OrganizationFactory(name='Partner Receive Handover'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.warehouse = PointOfInterestFactory(partner_organizations=[cls.partner], private=True, poi_type_id=1)
        cls.distribution_point = PointOfInterestFactory(partner_organizations=[cls.partner], private=True, poi_type_id=2)
        cls.hospital = PointOfInterestFactory(partner_organizations=[cls.partner], private=True, poi_type_id=3)
        cls.incoming = TransferFactory(
            partner_organization=cls.partner,
            destination_point=cls.warehouse,
            transfer_type=models.Transfer.DELIVERY
        )
        cls.checked_in = TransferFactory(
            partner_organization=cls.partner,
            status=models.Transfer.COMPLETED,
            destination_point=cls.warehouse
        )
        cls.outgoing = TransferFactory(
            partner_organization=cls.partner,
            origin_point=cls.warehouse,
            transfer_type=models.Transfer.DISTRIBUTION
        )
        cls.completed = TransferFactory(
            partner_organization=cls.partner,
            status=models.Transfer.COMPLETED,
            origin_point=cls.warehouse
        )
        cls.handover = TransferFactory(
            status=models.Transfer.PENDING,
            origin_point=cls.warehouse,
            transfer_type=models.Transfer.HANDOVER,
            from_partner_organization=cls.partner,
            partner_organization=cls.partner_receive_handover
        )
        cls.attachment = AttachmentFactory(
            file=SimpleUploadedFile('proof_file.pdf', b'Proof File'), code='proof_of_transfer')
        cls.material = MaterialFactory(number='1234', original_uom='EA')

    def test_get_parent_locations(self):
        serializer = PointOfInterestNotificationSerializer(self.warehouse).data
        self.assertEqual(serializer.get('parent_name'), str(self.warehouse.parent))
        self.assertEqual(serializer.get('region'), str(self.warehouse.parent.name))

        location_with_multiple_parents = PointOfInterestFactory(partner_organizations=[self.partner], private=True, poi_type_id=3)
        location_with_multiple_parents.parent = LocationFactory(admin_level=0, name='Country')
        location_with_multiple_parents.parent.parent = LocationFactory(admin_level=1, name='Region')
        location_with_multiple_parents.parent.parent.parent = LocationFactory(admin_level=2, name='State or Under')
        location_with_multiple_parents.save()
        serializer_with_multiple_parents = PointOfInterestNotificationSerializer(location_with_multiple_parents).data
        self.assertEqual(serializer_with_multiple_parents.get('parent_name'), f"{location_with_multiple_parents.parent.parent.parent.name} ({location_with_multiple_parents.parent.parent.parent.p_code})")
        self.assertEqual(serializer_with_multiple_parents.get('region'), location_with_multiple_parents.parent.parent.name)

    def test_incoming(self):
        url = reverse("last_mile:transfers-incoming", args=(self.warehouse.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.incoming.pk, response.data['results'][0]['id'])

    def test_checked_in(self):
        url = reverse('last_mile:transfers-checked-in', args=(self.warehouse.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.checked_in.pk, response.data['results'][0]['id'])

    def test_outgoing(self):
        url = reverse('last_mile:transfers-outgoing', args=(self.warehouse.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.outgoing.pk, response.data['results'][0]['id'])

    def test_completed(self):
        url = reverse('last_mile:transfers-completed', args=(self.warehouse.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Include also the Handover Transfer
        self.assertEqual(self.completed.pk, response.data['results'][1]['id'])
        self.assertEqual(self.handover.pk, response.data['results'][0]['id'])

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_full_checkin(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material, uom='EA')
        item_2 = ItemFactory(quantity=22, transfer=self.incoming, material=self.material, uom='CAR')
        item_3 = ItemFactory(quantity=33, transfer=self.incoming, material=self.material, uom='EA')

        PartnerMaterialFactory(material=self.material, partner_organization=self.partner)

        checkin_data = {
            "name": "checked in transfer",
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": item_1.quantity},
                {"id": item_2.pk, "quantity": item_2.quantity},
                {"id": item_3.pk, "quantity": item_3.quantity},
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, self.incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incoming.refresh_from_db()
        self.assertEqual(self.incoming.status, models.Transfer.COMPLETED)
        self.assertEqual("RUTF", response.data['items'][0]['material']['material_type_translate'])
        self.assertIn(self.attachment.filename, response.data['proof_file'])
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.initial_items[0]['quantity'], item_1.quantity)
        self.assertEqual(self.incoming.initial_items[1]['quantity'], item_2.quantity)
        self.assertEqual(self.incoming.initial_items[2]['quantity'], item_3.quantity)
        for existing, expected in zip(self.incoming.items.all().order_by('id'),
                                      sorted(checkin_data['items'], key=lambda x: x['id'])):
            self.assertEqual(existing.quantity, expected['quantity'])

        item_1.refresh_from_db()
        item_2.refresh_from_db()
        item_3.refresh_from_db()
        self.assertEqual(item_1.uom, item_1.base_uom)
        self.assertEqual(item_2.uom, item_2.base_uom)
        self.assertEqual(item_3.uom, item_3.base_uom)
        self.assertEqual(item_1.base_quantity, item_1.quantity)
        self.assertEqual(item_2.base_quantity, item_2.quantity)
        self.assertEqual(item_3.base_quantity, item_3.quantity)

        self.assertFalse(models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).exists())

        audit_logs = models.ItemAuditLog.objects.filter(
            item_id__in=[item_1.id, item_2.id, item_3.id]
        ).order_by('item_id', 'timestamp')

        self.assertEqual(audit_logs.count(), 3)

        item_1_audits = audit_logs.filter(item_id=item_1.id)
        if item_1_audits.exists():
            latest_audit = item_1_audits.latest('timestamp')
            self.assertEqual(latest_audit.action, models.ItemAuditLog.ACTION_CREATE)
            self.assertIsNotNone(latest_audit.transfer_info)

        # test new checkin of an already checked-in transfer
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The transfer was already checked-in.', response.data)

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_with_short(self):
        incoming = TransferFactory(
            partner_organization=self.partner,
            destination_point=self.warehouse,
            transfer_type=models.Transfer.DELIVERY,
            status=models.Transfer.PENDING
        )
        item_1 = ItemFactory(quantity=11, transfer=incoming, material=self.material)
        item_2 = ItemFactory(quantity=22, transfer=incoming, material=self.material)
        item_3 = ItemFactory(quantity=33, transfer=incoming, material=self.material)

        PartnerMaterialFactory(material=self.material, partner_organization=self.partner)

        checkin_data = {
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 11},
                {"id": item_3.pk, "quantity": 3},
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        incoming.refresh_from_db()
        self.assertEqual(incoming.initial_items[0]['quantity'], item_1.quantity)
        self.assertEqual(incoming.initial_items[1]['quantity'], item_2.quantity)
        self.assertEqual(incoming.initial_items[2]['quantity'], item_3.quantity)
        self.assertEqual(incoming.status, models.Transfer.COMPLETED)
        self.assertEqual("RUTF", response.data['items'][0]['material']['material_type_translate'])
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        self.assertIn(f'DW @ {checkin_data["destination_check_in_at"].strftime("%y-%m-%d")}', incoming.name)
        self.assertEqual(incoming.items.count(), len(response.data['items']))
        self.assertEqual(incoming.items.get(pk=item_1.pk).quantity, 11)
        self.assertEqual(incoming.items.get(pk=item_3.pk).quantity, 3)
        self.assertEqual(incoming.items.get(pk=item_1.pk).base_quantity, 11)
        self.assertEqual(incoming.items.get(pk=item_3.pk).base_quantity, 33)
        self.assertEqual(incoming.items.get(pk=item_1.pk).base_uom, "EA")
        self.assertEqual(incoming.items.get(pk=item_3.pk).base_uom, "EA")
        self.assertEqual(len(incoming.initial_items), 3)

        short_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).first()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.transfer_subtype, models.Transfer.SHORT)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 2)
        loss_item_2 = short_transfer.items.order_by('id').last()
        self.assertEqual(loss_item_2.quantity, 22)
        self.assertEqual(loss_item_2.base_quantity, 22)
        self.assertEqual(loss_item_2.base_uom, "EA")
        self.assertIn(incoming, loss_item_2.transfers_history.all())
        self.assertTrue(models.TransferHistory.objects.filter(origin_transfer_id=incoming.id).exists())
        self.assertEqual(short_transfer.items.order_by('id').first().quantity, 30)
        self.assertEqual(short_transfer.items.order_by('id').first().base_quantity, 33)
        self.assertEqual(short_transfer.items.order_by('id').first().base_uom, "EA")
        self.assertEqual(short_transfer.origin_transfer, incoming)

        checkin_audit_logs = models.ItemAuditLog.objects.filter(
            item_id__in=[item_1.id, item_3.id]
        )
        short_audit_logs = models.ItemAuditLog.objects.filter(
            item_id__in=[item.id for item in short_transfer.items.all()]
        )

        self.assertEqual(checkin_audit_logs.count(), 3)
        self.assertEqual(short_audit_logs.count(), 2)

        for audit_log in checkin_audit_logs:
            self.assertIn(audit_log.action, [
                models.ItemAuditLog.ACTION_UPDATE,
                models.ItemAuditLog.ACTION_CREATE
            ])
            self.assertIsNotNone(audit_log.transfer_info)

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_with_short_surplus(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        item_2 = ItemFactory(quantity=22, transfer=self.incoming, material=self.material)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming, material=self.material)

        PartnerMaterialFactory(material=self.material, partner_organization=self.partner)
        checkin_data = {
            "name": "checked in transfer",
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 11},
                {"id": item_2.pk, "quantity": 23},
                {"id": item_3.pk, "quantity": 3},
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, self.incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incoming.refresh_from_db()
        self.assertEqual(self.incoming.status, models.Transfer.COMPLETED)
        self.assertEqual("RUTF", response.data['items'][0]['material']['material_type_translate'])
        self.assertIn(response.data['proof_file'], self.attachment.file.path)
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 11)
        self.assertEqual(self.incoming.items.get(pk=item_2.pk).quantity, 22)
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).quantity, 3)
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).base_quantity, 11)
        self.assertEqual(self.incoming.items.get(pk=item_2.pk).base_quantity, 22)
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).base_quantity, 33)
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).base_uom, "EA")
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).base_uom, "EA")

        short_transfer = models.Transfer.objects.filter(
            transfer_type=models.Transfer.WASTAGE, transfer_subtype=models.Transfer.SHORT).first()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 1)
        short_item_3 = short_transfer.items.last()
        self.assertEqual(short_item_3.material.original_uom, short_item_3.base_uom)
        self.assertEqual(short_item_3.quantity, 30)
        self.assertEqual(short_item_3.base_quantity, 33)
        self.assertIn(self.incoming, short_item_3.transfers_history.all())

        surplus_transfer = models.Transfer.objects.filter(
            transfer_type=self.incoming.transfer_type, transfer_subtype=models.Transfer.SURPLUS).last()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 1)
        surplus_item_2 = surplus_transfer.items.last()
        self.assertEqual(surplus_item_2.quantity, 1)
        self.assertEqual(surplus_item_2.base_quantity, 22)
        self.assertEqual(surplus_item_2.material.original_uom, surplus_item_2.base_uom)
        self.assertIn(self.incoming, surplus_item_2.transfers_history.all())

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_RUFT_material(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        item_2 = ItemFactory(quantity=22, transfer=self.incoming)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming)

        PartnerMaterialFactory(material=self.material, partner_organization=self.partner)
        PartnerMaterialFactory(material=item_2.material, partner_organization=self.partner)
        PartnerMaterialFactory(material=item_3.material, partner_organization=self.partner)

        checkin_data = {
            "name": "checked in transfer",
            "comment": "",
            "proof_file": self.attachment.pk,

            "items": [
                {"id": item_1.pk, "quantity": 5},  # 1 RUFT
                {"id": item_3.pk, "quantity": 3},  # 1 non-RUFT item
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, self.incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incoming.refresh_from_db()
        self.assertEqual(self.incoming.status, models.Transfer.COMPLETED)
        response.data['items'] = sorted(response.data['items'], key=lambda x: x['id'])
        self.assertEqual("RUTF", response.data['items'][0]['material']['material_type_translate'])
        self.assertIn(response.data['proof_file'], self.attachment.file.path)
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.count(), 2)
        self.assertEqual(self.incoming.items.first().id, item_1.pk)
        self.assertEqual(self.incoming.items.first().base_quantity, 11)
        self.assertEqual(self.incoming.items.first().base_uom, self.incoming.items.first().material.original_uom)
        self.assertTrue(models.TransferHistory.objects.filter(origin_transfer_id=self.incoming.id).exists())
        item_1.refresh_from_db()
        self.assertEqual(self.incoming.items.first().quantity, item_1.quantity)

        not_hidden_item = models.Item.all_objects.get(pk=item_3.pk)
        self.assertEqual(not_hidden_item.hidden, False)
        self.assertEqual(not_hidden_item.quantity, 3)

        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 5)

        short_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).first()
        self.assertEqual(models.Item.all_objects.filter(transfer=short_transfer).count(), 3)  # 3 items on transfer
        self.assertEqual(short_transfer.items.count(), 3)

        loss_item_2 = short_transfer.items.first()
        self.assertEqual(loss_item_2.quantity, 6)
        self.assertIn(self.incoming, loss_item_2.transfers_history.all())

    def test_checkout_validation(self):
        destination = PointOfInterestFactory()
        item = ItemFactory(quantity=11, transfer=self.outgoing)

        checkout_data = {
            "transfer_type": models.Transfer.DISTRIBUTION,
            "destination_point": destination.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item.pk, "quantity": 12}
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Some of the items to be checked are no longer valid', response.data['items'])

    def test_checkout_distribution_location_validation(self):
        item = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.DISTRIBUTION,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item.pk, "quantity": 10}
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Destination location is mandatory at checkout.', response.data)

    def test_checkout_delivery_location_validation(self):
        item = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.DELIVERY,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item.pk, "quantity": 10}
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Destination location is mandatory at checkout.', response.data)

    def test_checkout_distribution(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        item_2 = ItemFactory(quantity=22, transfer=self.checked_in)
        item_3 = ItemFactory(quantity=33, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.DISTRIBUTION,
            "destination_point": self.hospital.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 11},
                {"id": item_3.pk, "quantity": 3},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual("Other", response.data['items'][0]['material']['material_type_translate'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.PENDING)
        self.assertEqual(response.data['transfer_type'], models.Transfer.DISTRIBUTION)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        checkout_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(checkout_transfer.destination_point, self.hospital)
        self.assertEqual(checkout_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(checkout_transfer.items.get(pk=item_1.pk).quantity, 11)
        self.assertTrue(models.TransferHistory.objects.filter(origin_transfer_id=checkout_transfer.id).exists())

        new_item_pk = [item['id'] for item in response.data['items'] if item['id'] != item_1.pk].pop()
        self.assertEqual(checkout_transfer.items.get(pk=new_item_pk).quantity, 3)
        for item in checkout_transfer.items.all():
            self.assertIn(self.checked_in, item.transfers_history.all())

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertEqual(self.checked_in.items.get(pk=item_3.pk).quantity, 30)

        checkout_item_audits = models.ItemAuditLog.objects.filter(
            item_id__in=[item.id for item in checkout_transfer.items.all()]
        )
        remaining_item_audits = models.ItemAuditLog.objects.filter(
            item_id__in=[item_2.id, item_3.id]
        )

        self.assertEqual(checkout_item_audits.count(), 3)
        for audit_log in checkout_item_audits:
            self.assertIn(audit_log.action, [
                models.ItemAuditLog.ACTION_CREATE,
                models.ItemAuditLog.ACTION_UPDATE
            ])
            self.assertIsNotNone(audit_log.transfer_info)

        remaining_item_3_audits = remaining_item_audits.filter(item_id=item_3.id)
        if remaining_item_3_audits.exists():
            latest_audit = remaining_item_3_audits.latest('timestamp')
            self.assertEqual(latest_audit.action, models.ItemAuditLog.ACTION_UPDATE)
            self.assertIn('quantity', latest_audit.changed_fields)
            self.assertEqual(latest_audit.old_values['quantity'], 33)
            self.assertEqual(latest_audit.new_values['quantity'], 30)

    def test_checkout_wastage(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        item_2 = ItemFactory(quantity=22, transfer=self.checked_in)

        destination = PointOfInterestFactory()
        checkout_data = {
            "transfer_type": models.Transfer.WASTAGE,
            "destination_point": destination.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 9, "wastage_type": models.Item.EXPIRED},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        mock_send = Mock()
        with patch("etools.applications.last_mile.tasks.send_notification", mock_send):
            response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual("Other", response.data['items'][0]['material']['material_type_translate'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(response.data['transfer_type'], models.Transfer.WASTAGE)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        wastage_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(wastage_transfer.destination_point, destination)
        self.assertEqual(wastage_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(wastage_transfer.items.first().quantity, 9)
        self.assertEqual(wastage_transfer.items.first().wastage_type, models.Item.EXPIRED)

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_1.pk).quantity, 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertIn(f'W @ {checkout_data["origin_check_out_at"].strftime("%y-%m-%d")}', wastage_transfer.name)

        self.assertEqual(mock_send.call_count, 1)

        wastage_item_audits = models.ItemAuditLog.objects.filter(
            item_id__in=[item.id for item in wastage_transfer.items.all()]
        )
        remaining_item_audits = models.ItemAuditLog.objects.filter(item_id=item_1.id)

        self.assertEqual(wastage_item_audits.count(), 1)
        wastage_audit = wastage_item_audits.first()
        self.assertEqual(wastage_audit.action, models.ItemAuditLog.ACTION_CREATE)
        self.assertEqual(wastage_audit.user, self.partner_staff)
        self.assertEqual(wastage_audit.new_values['wastage_type'], models.Item.EXPIRED)
        self.assertEqual(wastage_audit.new_values['quantity'], 9)

        remaining_audits = remaining_item_audits.filter(
            action=models.ItemAuditLog.ACTION_UPDATE
        ).order_by('-timestamp')
        if remaining_audits.exists():
            quantity_update_audit = remaining_audits.first()
            self.assertIn('quantity', quantity_update_audit.changed_fields)
            self.assertEqual(quantity_update_audit.old_values['quantity'], 11)
            self.assertEqual(quantity_update_audit.new_values['quantity'], 2)

    def test_checkout_dispense(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        item_2 = ItemFactory(quantity=22, transfer=self.checked_in)

        destination = PointOfInterestFactory()
        checkout_data = {
            "transfer_type": models.Transfer.DISPENSE,
            "destination_point": destination.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 9}
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))

        mock_send = Mock()
        with patch("etools.applications.last_mile.tasks.send_notification", mock_send):
            response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        mock_send.assert_called_once()

        self.assertEqual("Other", response.data['items'][0]['material']['material_type_translate'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(response.data['transfer_type'], models.Transfer.DISPENSE)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        dispense_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(dispense_transfer.destination_point, destination)
        self.assertEqual(dispense_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(dispense_transfer.items.first().quantity, 9)
        self.assertEqual(dispense_transfer.items.first().wastage_type, None)

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_1.pk).quantity, 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertIn(f'D @ {checkout_data["origin_check_out_at"].strftime("%y-%m-%d")}', dispense_transfer.name)

    def test_checkout_handover(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        item_2 = ItemFactory(quantity=22, transfer=self.checked_in)
        destination = PointOfInterestFactory()
        agreement = AgreementFactory()
        checkout_data = {
            "transfer_type": models.Transfer.HANDOVER,
            "destination_point": destination.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "partner_id": agreement.partner.id,
            "items": [
                {"id": item_1.pk, "quantity": 9},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual("Other", response.data['items'][0]['material']['material_type_translate'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.PENDING)
        self.assertEqual(response.data['transfer_type'], models.Transfer.HANDOVER)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        handover_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(handover_transfer.partner_organization, agreement.partner)
        self.assertEqual(handover_transfer.destination_point, destination)
        self.assertEqual(handover_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(handover_transfer.items.first().quantity, 9)
        self.assertEqual(handover_transfer.recipient_partner_organization.id, agreement.partner.id)
        self.assertEqual(handover_transfer.from_partner_organization.id, self.partner.pk)
        self.assertEqual(len(handover_transfer.initial_items), 1)
        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_1.pk).quantity, 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertIn(f'HO @ {checkout_data["origin_check_out_at"].strftime("%y-%m-%d")}', handover_transfer.name)

    def test_checkout_handover_partner_validation(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        destination = PointOfInterestFactory()
        checkout_data = {
            "transfer_type": models.Transfer.HANDOVER,
            "destination_point": destination.pk,
            "comment": "",
            "proof_file": self.attachment.pk,
            "partner_id": self.partner.id,
            "items": [
                {"id": item_1.pk, "quantity": 9},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The provided partner is not eligible for a handover.', response.data['partner_id'][0])

        checkout_data['partner_id'] = self.partner_staff.partner.id
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The provided partner is not eligible for a handover.', response.data['partner_id'][0])

    def test_checkout_wastage_without_location(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.WASTAGE,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 9, "wastage_type": models.Item.EXPIRED},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(response.data['transfer_type'], models.Transfer.WASTAGE)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        wastage_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(wastage_transfer.destination_point, None)

    def test_checkout_dispense_without_location(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.DISPENSE,
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 9}
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(response.data['transfer_type'], models.Transfer.DISPENSE)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        dispense_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(dispense_transfer.destination_point, None)

    def test_checkout_without_proof_file(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.WASTAGE,
            "comment": "",
            "items": [
                {"id": item_1.pk, "quantity": 9, "wastage_type": models.Item.EXPIRED},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The proof file is required.', response.data)

    def test_checkout_without_proof_file_dispense(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)

        checkout_data = {
            "transfer_type": models.Transfer.DISPENSE,
            "comment": "",
            "items": [
                {"id": item_1.pk, "quantity": 9},
            ],
            "origin_check_out_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The proof file is required.', response.data)

    @skip('disabling feature for now')
    def test_mark_completed(self):
        self.assertEqual(self.outgoing.status, models.Transfer.PENDING)

        self.assertEqual(self.outgoing.transfer_type, models.Transfer.DISTRIBUTION)

        url = reverse('last_mile:transfers-mark-complete', args=(self.warehouse.pk, self.outgoing.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.outgoing.refresh_from_db()
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(self.outgoing.status, models.Transfer.COMPLETED)
        self.assertEqual(self.outgoing.checked_in_by, self.partner_staff)

    def test_item_expiry_ordering(self):
        item_1 = ItemFactory(transfer=self.outgoing, expiry_date=timezone.now() + datetime.timedelta(days=30))
        item_2 = ItemFactory(transfer=self.outgoing, expiry_date=timezone.now() + datetime.timedelta(days=20))
        item_3 = ItemFactory(transfer=self.outgoing, expiry_date=timezone.now() + datetime.timedelta(days=10))

        url = reverse('last_mile:transfers-details', args=(self.warehouse.pk, self.outgoing.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item_3.pk, item_2.pk, item_1.pk], [i['id'] for i in response.data['items']])

    def test_upload_evidence(self):
        url = reverse('last_mile:transfers-upload-evidence', args=(self.warehouse.pk, self.completed.pk))
        attachment = AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!'))
        data = {'evidence_file': attachment.id, 'comment': 'some comment'}
        self.assertNotEqual(self.completed.transfer_type, self.completed.WASTAGE)

        response = self.forced_auth_req('post', url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Evidence files are only for wastage transfers.', response.data)

        self.completed.transfer_type = self.completed.WASTAGE
        self.completed.save(update_fields=['transfer_type'])
        self.assertEqual(self.completed.transfer_type, self.completed.WASTAGE)
        self.assertEqual(self.completed.transfer_evidences.count(), 0)

        response = self.forced_auth_req('post', url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.completed.transfer_evidences.count(), 1)


class TestItemUpdateViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.poi_partner = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)
        cls.transfer = TransferFactory(destination_point=cls.poi_partner, partner_organization=cls.partner)
        cls.other = {
            'uom_map': {
                'EA': 1,
                'PAC': 10,
                'CAR': 50
            }
        }
        cls.material = MaterialFactory(original_uom='PAC', other=cls.other)

    def test_patch(self):
        item = ItemFactory(transfer=self.transfer)
        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'description': 'updated description',
            'uom': 'KG'
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = models.Item.objects.get(pk=item.pk)
        self.assertEqual(item.description, 'updated description')
        self.assertEqual(item.mapped_description, 'updated description')
        self.assertEqual(item.uom, 'KG')
        self.assertEqual(response.data['uom'], 'KG')

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 2)

        update_audits = audit_logs.filter(action=models.ItemAuditLog.ACTION_UPDATE)
        if update_audits.exists():
            update_audit = update_audits.latest('timestamp')
            self.assertIn('mapped_description', update_audit.changed_fields)
            self.assertIn('uom', update_audit.changed_fields)
            self.assertEqual(update_audit.new_values['mapped_description'], 'updated description')
            self.assertEqual(update_audit.new_values['uom'], 'KG')

    def test_patch_already_updated_description(self):
        item = ItemFactory(transfer=self.transfer)
        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'description': 'updated description',
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        del item.__dict__['mapped_description']  # Clear the cached_property
        del item.__dict__['description']
        item.refresh_from_db()
        self.assertEqual(item.mapped_description, 'updated description')
        self.assertEqual(item.description, 'updated description')
        data = {
            'description': 'updated description12',
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The description cannot be modified. A value is already present", str(response.data))

    def test_patch_item_with_uom(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            "conversion_factor": 150,
            "description": "updated description",
            "uom": "PAC"
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)
        item.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(item.mapped_description, 'updated description')
        self.assertEqual(item.uom, 'PAC')

    def test_update_description_without_conversion_factor(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            "description": "updated description",
            "uom": "PAC"
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)
        item.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(item.mapped_description, 'updated description')
        self.assertEqual(item.uom, 'PAC')

    def test_patch_uom_mappings(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'uom': 'CAR',
            'conversion_factor': 10 / 50,
            'quantity': 20
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(float(item.conversion_factor), 10 / 50)
        self.assertEqual(item.quantity, 20)
        self.assertEqual(item.uom, 'CAR')
        self.assertEqual(item.mapped_description, None)

    def test_patch_no_uom_map(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'uom': 'BAG',
            'conversion_factor': 10 / 50,
            'quantity': 20
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The provided uom is not available in the material mapping.', response.data['non_field_errors'][0])

    def test_patch_wrong_factor(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'uom': 'CAR',
            'conversion_factor': 0.25,
            'quantity': 20
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The conversion_factor is incorrect.', response.data['non_field_errors'][0])

    def test_patch_wrong_qty(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)

        url = reverse('last_mile:item-update-detail', args=(item.pk,))
        data = {
            'uom': 'CAR',
            'conversion_factor': 0.2,
            'quantity': 24
        }
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The calculated quantity is incorrect.', response.data['non_field_errors'][0])

    def test_post_split(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)
        self.assertEqual(self.transfer.items.count(), 1)
        url = reverse('last_mile:item-update-split', args=(item.pk,))
        data = {
            'quantities': [76, 24]
        }
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.transfer.items.count(), 2)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 76)
        self.assertEqual(item.base_quantity, 100)
        self.assertEqual(item.base_uom, item.material.original_uom)
        self.assertEqual(self.transfer.items.exclude(pk=item.pk).first().quantity, 24)
        self.assertEqual(self.transfer.items.exclude(pk=item.pk).first().base_quantity, 100)
        self.assertEqual(self.transfer.items.exclude(pk=item.pk).first().base_uom, item.material.original_uom)

        new_item = self.transfer.items.exclude(pk=item.pk).first()

        original_item_audits = models.ItemAuditLog.objects.filter(item_id=item.id)
        update_audits = original_item_audits.filter(action=models.ItemAuditLog.ACTION_UPDATE)
        self.assertEqual(update_audits.count(), 1)

        latest_update = update_audits.latest('timestamp')
        self.assertIn('quantity', latest_update.changed_fields)
        self.assertEqual(latest_update.old_values['quantity'], 100)
        self.assertEqual(latest_update.new_values['quantity'], 76)

        new_item_audits = models.ItemAuditLog.objects.filter(item_id=new_item.id)
        create_audits = new_item_audits.filter(action=models.ItemAuditLog.ACTION_CREATE)
        self.assertEqual(create_audits.count(), 1)

        create_audit = create_audits.first()
        self.assertEqual(create_audit.new_values['quantity'], 24)
        self.assertIsNotNone(create_audit.transfer_info)

    def test_post_split_validation(self):
        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)
        self.assertEqual(self.transfer.items.count(), 1)
        url = reverse('last_mile:item-update-split', args=(item.pk,))
        data = {
            'quantities': [76, 25]
        }
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Incorrect split values.', response.data['quantities'][0])

        data['quantities'] = [1, 2, 97]
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Incorrect split values.', response.data['quantities'][0])


class TestItemAuditLogViewWorkflow(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Audit Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.warehouse = PointOfInterestFactory(partner_organizations=[cls.partner], poi_type_id=1)
        cls.hospital = PointOfInterestFactory(partner_organizations=[cls.partner], poi_type_id=3)
        cls.material = MaterialFactory(number='AUD001', original_uom='EA')

    def setUp(self):
        models.ItemAuditLog.objects.all().delete()

    def test_complete_transfer_workflow_audit_trail(self):

        PartnerMaterialFactory(partner_organization=self.partner, material=self.material)

        incoming_transfer = TransferFactory(
            partner_organization=self.partner,
            destination_point=self.warehouse,
            transfer_type=models.Transfer.DELIVERY,
            status=models.Transfer.PENDING
        )

        item_1 = ItemFactory(quantity=100, transfer=incoming_transfer, material=self.material)
        item_2 = ItemFactory(quantity=200, transfer=incoming_transfer, material=self.material)

        initial_audit_count = models.ItemAuditLog.objects.count()
        self.assertEqual(initial_audit_count, 2)

        attachment = AttachmentFactory(file=SimpleUploadedFile('test.pdf', b'test content'))
        attachment_delivery = AttachmentFactory(file=SimpleUploadedFile('test_delivery.pdf', b'test content'))
        checkin_data = {
            "name": "Audit Test Check-in",
            "comment": "Testing audit trail",
            "proof_file": attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 95},
                {"id": item_2.pk, "quantity": 200}
            ],
            "destination_check_in_at": timezone.now()
        }

        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, incoming_transfer.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        checkin_audit_count = models.ItemAuditLog.objects.count()
        self.assertGreater(checkin_audit_count, initial_audit_count)

        short_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).first()
        short_transfer.refresh_from_db()
        if short_transfer:
            item_ids = [item.id for item in short_transfer.items.all()]
            short_transfer_audits = models.ItemAuditLog.objects.filter(
                item_id__in=item_ids
            )

            self.assertGreater(short_transfer_audits.count(), 0)

        item_1.refresh_from_db()
        item_2.refresh_from_db()

        checkout_data = {
            "transfer_type": models.Transfer.DISTRIBUTION,
            "destination_point": self.hospital.pk,
            "comment": "Distribution for audit test",
            "proof_file": attachment_delivery.pk,
            "items": [
                {"id": item_1.pk, "quantity": 50},
                {"id": item_2.pk, "quantity": 100}
            ],
            "origin_check_out_at": timezone.now()
        }

        url = reverse('last_mile:transfers-new-check-out', args=(self.warehouse.pk,))
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        distribution_audit_count = models.ItemAuditLog.objects.count()
        self.assertGreater(distribution_audit_count, checkin_audit_count)

        distribution_transfer = models.Transfer.objects.get(pk=response.data['id'])

        distribution_items = list(distribution_transfer.items.all())
        for i, item in enumerate(distribution_items):
            url = reverse('last_mile:item-update-detail', args=(item.pk,))
            update_data = {
                'description': f'Updated description {i+1}',
                'uom': 'KG'
            }
            response = self.forced_auth_req('patch', url, user=self.partner_staff, data=update_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_audit_count = models.ItemAuditLog.objects.count()
        self.assertGreater(update_audit_count, distribution_audit_count)

        split_item = distribution_items[0]
        url = reverse('last_mile:item-update-split', args=(split_item.pk,))
        split_data = {'quantities': [20, 30]}

        response = self.forced_auth_req('post', url, user=self.partner_staff, data=split_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        split_audit_count = models.ItemAuditLog.objects.count()
        self.assertGreater(split_audit_count, update_audit_count)

        all_audits = models.ItemAuditLog.objects.all().order_by('timestamp')

        action_types = set(all_audits.values_list('action', flat=True))
        self.assertIn(models.ItemAuditLog.ACTION_CREATE, action_types)
        self.assertIn(models.ItemAuditLog.ACTION_UPDATE, action_types)

        user_audits = all_audits.filter(user=self.partner_staff)
        self.assertGreater(user_audits.count(), 0)

        for audit in all_audits:
            if audit.action != models.ItemAuditLog.ACTION_DELETE:
                self.assertIsNotNone(audit.transfer_info)

    def test_audit_log_data_integrity_across_operations(self):
        transfer = TransferFactory(partner_organization=self.partner, destination_point=self.warehouse)
        item = ItemFactory(quantity=100, transfer=transfer, material=self.material, batch_id='INTEGRITY_TEST')

        models.ItemAuditLog.objects.all().delete()

        operations = [
            {'quantity': 90, 'mapped_description': 'First update'},
            {'quantity': 80, 'batch_id': 'UPDATED_BATCH'},
            {'quantity': 70, 'wastage_type': models.Item.EXPIRED},
            {'quantity': 60, 'wastage_type': None},
        ]

        for _, update_data in enumerate(operations):
            for field, value in update_data.items():
                setattr(item, field, value)
            item.save()

            latest_audit = models.ItemAuditLog.objects.filter(item_id=item.id).latest('timestamp')
            self.assertEqual(latest_audit.action, models.ItemAuditLog.ACTION_UPDATE)

            for field, new_value in update_data.items():
                if field in latest_audit.changed_fields:
                    self.assertEqual(latest_audit.new_values[field], new_value)

        all_item_audits = models.ItemAuditLog.objects.filter(item_id=item.id).order_by('timestamp')
        self.assertEqual(all_item_audits.count(), len(operations))

    def test_audit_log_performance_with_bulk_workflow_operations(self):
        items = []

        start_time = timezone.now()

        for i in range(10):
            transfer = TransferFactory(
                partner_organization=self.partner,
                destination_point=self.warehouse,
                name=f'Bulk Transfer {i}'
            )

            for j in range(5):
                item = ItemFactory(
                    quantity=100 + j,
                    transfer=transfer,
                    material=self.material,
                    batch_id=f'BULK_{i}_{j}'
                )
                items.append(item)

        creation_time = (timezone.now() - start_time).total_seconds()

        models.ItemAuditLog.objects.all().delete()

        start_time = timezone.now()
        for i, item in enumerate(items):
            item.quantity = item.quantity * 2
            item.mapped_description = f'Bulk updated {i}'
            item.save()

        update_time = (timezone.now() - start_time).total_seconds()

        self.assertLess(creation_time, 2.0)
        self.assertLess(update_time, 2.0)

        total_audits = models.ItemAuditLog.objects.count()
        self.assertEqual(total_audits, len(items))

        for item in items:
            audit = models.ItemAuditLog.objects.filter(item_id=item.id).first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.action, models.ItemAuditLog.ACTION_UPDATE)
            self.assertIn('quantity', audit.changed_fields)
            self.assertIn('mapped_description', audit.changed_fields)
            self.assertIsNotNone(audit.transfer_info)
