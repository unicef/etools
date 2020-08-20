from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import FileType, Intervention
from etools.applications.partners.tests.factories import (
    FileTypeFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.partnership_manager = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])

        cls.draft_intervention = InterventionFactory()

        country_programme = CountryProgrammeFactory()
        cls.signed_intervention = InterventionFactory(
            status=Intervention.SIGNED,
            signed_by_partner_date=timezone.now(),
            partner_authorized_officer_signatory=PartnerStaffFactory(),
            signed_by_unicef_date=timezone.now(),
            country_programme=country_programme,
            start=timezone.now(),
            end=timezone.now() + timedelta(days=1),
            agreement__country_programme=country_programme,
        )
        InterventionBudgetFactory(intervention=cls.signed_intervention, unicef_cash_local=1)
        AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
            code='partners_intervention_signed_pd',
            content_object=cls.signed_intervention,
        )
        cls.signed_intervention.unicef_focal_points.add(UserFactory())
        cls.signed_intervention.sections.add(SectionFactory())
        cls.signed_intervention.offices.add(OfficeFactory())
        cls.signed_intervention.partner_focal_points.add(PartnerStaffFactory())


class TestRisksManagement(BaseTestCase):
    pass


class TestProgrammaticVisitsManagement(BaseTestCase):
    pass


class TestFinancialManagement(BaseTestCase):
    # todo: update after changing field to array
    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': Intervention.CASH_TRANSFER_PAYMENT,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['cash_transfer_modalities'], Intervention.CASH_TRANSFER_PAYMENT)

    def test_update_signed(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.signed_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': Intervention.CASH_TRANSFER_PAYMENT,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in signed: cash_transfer_modalities', response.data[0])


class TestFundsReservationManagement(BaseTestCase):
    pass


class TestSignedDocumentsManagement(BaseTestCase):
    pass


class TestAmendmentsManagement(BaseTestCase):
    pass


class TestFinalPartnershipReviewManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
        )
        FileTypeFactory(name=FileType.FINAL_PARTNERSHIP_REVIEW)

    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'final_partnership_review': self.example_attachment.id,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], True)
        self.assertIn('hello_world.txt', response.data['final_partnership_review']['attachment'])
        self.assertEqual(
            self.draft_intervention.attachments.get(
                type__name=FileType.FINAL_PARTNERSHIP_REVIEW
            ).attachment_file.get().pk,
            self.example_attachment.pk
        )

    def test_update_permissions_restricted(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.signed_intervention.pk]),
            user=self.partnership_manager,
            data={
                'final_partnership_review': self.example_attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'Cannot change fields while in signed: final_partnership_review')
