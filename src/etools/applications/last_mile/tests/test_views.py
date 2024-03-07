from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.tests.factories import ItemFactory, PointOfInterestFactory, TransferFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestPointOfInterestTypeView(BaseTenantTestCase):
    fixtures = ('poi_type.json',)
    url = reverse('last_mile:poi-types-list')

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.partner.organization,
        )

    def test_api_poi_types_list(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)


class TestPointOfInterestView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.partner.organization,
        )
        cls.poi_partner = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)

    def test_api_poi_list(self):
        url = reverse("last_mile:pois-list")
        PointOfInterestFactory(private=True)

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.poi_partner.pk, response.data['results'][0]['id'])

    def test_api_item_list(self):
        url = reverse('last_mile:pois-items', args=(self.poi_partner.pk,))
        transfer = TransferFactory(status=models.Transfer.COMPLETED, destination_point=self.poi_partner)
        for i in range(5):
            ItemFactory(transfer=transfer)

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_upload_waybill(self):
        url = reverse('last_mile:pois-upload-waybill', args=(self.poi_partner.pk,))
        attachment = AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!'))

        self.assertEqual(models.Transfer.objects.count(), 0)

        response = self.forced_auth_req('post', url, user=self.partner_staff, data={'waybill_file': attachment.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(models.Transfer.objects.count(), 1)
        self.assertEqual(response.data['destination_point']['id'], self.poi_partner.pk)
        self.assertEqual(response.data['checked_in_by']['id'], self.partner_staff.pk)
        self.assertEqual(response.data['transfer_type'], models.Transfer.WAYBILL)
        self.assertIn(attachment.filename, response.data['waybill_file'])


class TestTransferView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.partner.organization,
        )
        cls.poi_partner_1 = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)
        cls.poi_partner_2 = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)
        cls.poi_partner_3 = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)
        cls.incoming = TransferFactory(
            partner_organization=cls.partner, destination_point=cls.poi_partner_1
        )
        cls.checked_in = TransferFactory(
            partner_organization=cls.partner, status=models.Transfer.COMPLETED, destination_point=cls.poi_partner_1
        )
        cls.outgoing = TransferFactory(
            partner_organization=cls.partner, origin_point=cls.poi_partner_1
        )
        cls.completed = TransferFactory(
            partner_organization=cls.partner, status=models.Transfer.COMPLETED, origin_point=cls.poi_partner_1
        )

    def test_incoming(self):
        url = reverse("last_mile:transfers-incoming", args=(self.poi_partner_1.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.incoming.pk, response.data['results'][0]['id'])

    def test_checked_in(self):
        url = reverse('last_mile:transfers-checked-in', args=(self.poi_partner_1.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.checked_in.pk, response.data['results'][0]['id'])

    def test_outgoing(self):
        url = reverse('last_mile:transfers-outgoing', args=(self.poi_partner_1.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.outgoing.pk, response.data['results'][0]['id'])

    def test_completed(self):
        url = reverse('last_mile:transfers-completed', args=(self.poi_partner_1.pk,))
        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self.completed.pk, response.data['results'][0]['id'])

    def test_partial_checkin(self):
        item_1 = ItemFactory(quantity=11, transfer=self.incoming)
        item_2 = ItemFactory(quantity=22, transfer=self.incoming)
        item_3 = ItemFactory(quantity=33, transfer=self.incoming)
        attachment = AttachmentFactory(file=SimpleUploadedFile('proof_file.pdf', b'Proof File'))

        checkin_data = {
            "name": "checked in transfer",
            "comment": "",
            "proof_file": attachment.pk,
            "items": [
                {"id": item_1.pk, "quantity": 11},
                {"id": item_3.pk, "quantity": 3},
            ],
            "destination_check_in_at": timezone.now()
        }
        url = reverse('last_mile:transfers-new-check-in', args=(self.poi_partner_1.pk, self.incoming.pk))
        response = self.forced_auth_req('patch', url, user=self.partner_staff, data=checkin_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incoming.refresh_from_db()
        self.assertIn(attachment.filename, response.data['proof_file'])
        self.assertEqual(self.incoming.name, checkin_data['name'])
        self.assertEqual(self.incoming.items.count(), len(response.data['items']))
        self.assertEqual(self.incoming.items.get(pk=item_1.pk).quantity, 11)
        self.assertEqual(self.incoming.items.get(pk=item_3.pk).quantity, 3)

        loss_transfer = models.Transfer.objects.filter(transfer_type=models.Transfer.LOSS).first()
        self.assertEqual(loss_transfer.items.count(), 2)
        loss_item_2 = loss_transfer.items.get(pk=item_2.pk)
        self.assertEqual(loss_item_2.quantity, 22)
        self.assertIn(self.incoming, loss_item_2.transfers_history.all())
        self.assertEqual(loss_transfer.items.last().quantity, 30)
        self.assertEqual(loss_transfer.origin_transfer, self.incoming)
