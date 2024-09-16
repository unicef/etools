import datetime
from unittest import skip
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.tests.factories import (
    ItemFactory,
    MaterialFactory,
    PointOfInterestFactory,
    TransferFactory,
)
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Agreement
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
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
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
        cls.attachment = AttachmentFactory(
            file=SimpleUploadedFile('proof_file.pdf', b'Proof File'), code='proof_of_transfer')
        cls.material = MaterialFactory(number='1234')

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
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.completed.pk, response.data['results'][0]['id'])

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_full_checkin(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        item_2 = ItemFactory(quantity=22, transfer=self.incoming, material=self.material)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming, material=self.material)

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
        self.assertIn(self.attachment.filename, response.data['proof_file'])
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        for existing, expected in zip(self.incoming.items.all().order_by('id'),
                                      sorted(checkin_data['items'], key=lambda x: x['id'])):
            self.assertEqual(existing.quantity, expected['quantity'])

        self.assertFalse(models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).exists())

        # test new checkin of an already checked-in transfer
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The transfer was already checked-in.', response.data)

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_with_short(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        ItemFactory(quantity=22, transfer=self.incoming, material=self.material)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming, material=self.material)

        checkin_data = {
            "comment": "",
            "proof_file": self.attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 11},
                {"id": item_3.pk, "quantity": 3},
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.warehouse.pk, self.incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incoming.refresh_from_db()
        self.assertEqual(self.incoming.status, models.Transfer.COMPLETED)
        self.assertIn(response.data['proof_file'], self.attachment.file_link)

        self.assertIn(f'DW @ {checkin_data["destination_check_in_at"].strftime("%y-%m-%d")}', self.incoming.name)
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 11)
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).quantity, 3)

        short_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).first()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.transfer_subtype, models.Transfer.SHORT)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 2)
        loss_item_2 = short_transfer.items.order_by('id').last()
        self.assertEqual(loss_item_2.quantity, 22)
        self.assertIn(self.incoming, loss_item_2.transfers_history.all())
        self.assertEqual(short_transfer.items.order_by('id').first().quantity, 30)
        self.assertEqual(short_transfer.origin_transfer, self.incoming)

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_with_short_surplus(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        item_2 = ItemFactory(quantity=22, transfer=self.incoming, material=self.material)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming, material=self.material)

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
        self.assertIn(response.data['proof_file'], self.attachment.file_link)
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 11)
        self.assertEqual(self.incoming.items.get(pk=item_2.pk).quantity, 22)
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).quantity, 3)

        short_transfer = models.Transfer.objects.filter(
            transfer_type=models.Transfer.WASTAGE, transfer_subtype=models.Transfer.SHORT).first()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 1)
        short_item_3 = short_transfer.items.last()
        self.assertEqual(short_item_3.quantity, 30)
        self.assertIn(self.incoming, short_item_3.transfers_history.all())

        surplus_transfer = models.Transfer.objects.filter(
            transfer_type=self.incoming.transfer_type, transfer_subtype=models.Transfer.SURPLUS).last()
        self.assertEqual(short_transfer.status, models.Transfer.COMPLETED)
        self.assertEqual(short_transfer.destination_check_in_at, checkin_data['destination_check_in_at'])
        self.assertEqual(short_transfer.items.count(), 1)
        surplus_item_2 = surplus_transfer.items.last()
        self.assertEqual(surplus_item_2.quantity, 1)
        self.assertIn(self.incoming, surplus_item_2.transfers_history.all())

    @override_settings(RUTF_MATERIALS=['1234'])
    def test_partial_checkin_RUFT_material(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming, material=self.material)
        ItemFactory(quantity=22, transfer=self.incoming)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming)

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
        self.assertIn(response.data['proof_file'], self.attachment.file_link)
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.count(), 1)  # only 1 checked-in item is visible, non RUFT
        self.assertEqual(self.incoming.items.first().id, item_1.pk)
        item_1.refresh_from_db()
        self.assertEqual(self.incoming.items.first().quantity, item_1.quantity)

        hidden_item = models.Item.all_objects.get(pk=item_3.pk)
        self.assertEqual(hidden_item.hidden, True)
        self.assertEqual(hidden_item.quantity, 3)

        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 5)

        short_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.WASTAGE).first()
        self.assertEqual(models.Item.all_objects.filter(transfer=short_transfer).count(), 3)  # 3 items on transfer
        self.assertEqual(short_transfer.items.count(), 1)  # only 1 visible item

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.PENDING)
        self.assertEqual(response.data['transfer_type'], models.Transfer.DISTRIBUTION)
        self.assertIn(response.data['proof_file'], self.attachment.file_link)

        checkout_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(checkout_transfer.destination_point, self.hospital)
        self.assertEqual(checkout_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(checkout_transfer.items.get(pk=item_1.pk).quantity, 11)

        new_item_pk = [item['id'] for item in response.data['items'] if item['id'] != item_1.pk].pop()
        self.assertEqual(checkout_transfer.items.get(pk=new_item_pk).quantity, 3)
        for item in checkout_transfer.items.all():
            self.assertIn(self.checked_in, item.transfers_history.all())

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertEqual(self.checked_in.items.get(pk=item_3.pk).quantity, 30)

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
        response = self.forced_auth_req('post', url, user=self.partner_staff, data=checkout_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.COMPLETED)
        self.assertEqual(response.data['transfer_type'], models.Transfer.WASTAGE)
        self.assertIn(response.data['proof_file'], self.attachment.file_link)

        wastage_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(wastage_transfer.destination_point, destination)
        self.assertEqual(wastage_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(wastage_transfer.items.first().quantity, 9)
        self.assertEqual(wastage_transfer.items.first().wastage_type, models.Item.EXPIRED)

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_1.pk).quantity, 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertIn(f'W @ {checkout_data["origin_check_out_at"].strftime("%y-%m-%d")}', wastage_transfer.name)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], models.Transfer.PENDING)
        self.assertEqual(response.data['transfer_type'], models.Transfer.HANDOVER)
        self.assertIn(response.data['proof_file'], self.attachment.file.path)

        handover_transfer = models.Transfer.objects.get(pk=response.data['id'])
        self.assertEqual(handover_transfer.partner_organization, agreement.partner)
        self.assertEqual(handover_transfer.destination_point, destination)
        self.assertEqual(handover_transfer.items.count(), len(checkout_data['items']))
        self.assertEqual(handover_transfer.items.first().quantity, 9)

        self.assertEqual(self.checked_in.items.count(), 2)
        self.assertEqual(self.checked_in.items.get(pk=item_1.pk).quantity, 2)
        self.assertEqual(self.checked_in.items.get(pk=item_2.pk).quantity, 22)
        self.assertIn(f'HO @ {checkout_data["origin_check_out_at"].strftime("%y-%m-%d")}', handover_transfer.name)

    def test_checkout_handover_partner_validation(self):
        item_1 = ItemFactory(quantity=11, transfer=self.checked_in)
        destination = PointOfInterestFactory()
        agreement = AgreementFactory(status=Agreement.DRAFT)
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
        item.refresh_from_db()
        self.assertEqual(item.description, 'updated description')
        self.assertEqual(response.data['description'], 'updated description')
        self.assertEqual(item.uom, 'KG')
        self.assertEqual(response.data['uom'], 'KG')

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
        self.assertEqual(self.transfer.items.exclude(pk=item.pk).first().quantity, 24)

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
