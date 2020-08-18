from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionBudgetFactory,
    InterventionFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class TestRisksManagement(BaseTenantTestCase):
    pass


class TestProgrammaticVisitsManagement(BaseTenantTestCase):
    pass


class TestFinancialManagement(BaseTenantTestCase):
    pass


class TestFundsReservationManagement(BaseTenantTestCase):
    pass


class TestSignedDocumentsManagement(BaseTenantTestCase):
    pass


class TestAmendmentsManagement(BaseTenantTestCase):
    pass


class TestFinalPartnershipReviewManagement(BaseTenantTestCase):
    def test_update(self):
        intervention = InterventionFactory()
        attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'prc_review_attachment': attachment.id,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['prc_review_attachment'], True)
        self.assertIn('hello_world.txt', response.data['prc_review_attachment'])
        self.assertIsNotNone(response.data['submission_date_prc'])

    def test_update_not_in_draft(self):
        country_programme = CountryProgrammeFactory()
        intervention = InterventionFactory(
            status=Intervention.SIGNED,
            signed_by_partner_date=timezone.now(),
            partner_authorized_officer_signatory=PartnerStaffFactory(),
            signed_by_unicef_date=timezone.now(),
            country_programme=country_programme,
            start=timezone.now(),
            end=timezone.now() + timedelta(days=1),
            agreement__country_programme=country_programme,
        )
        InterventionBudgetFactory(intervention=intervention, unicef_cash_local=1)
        AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
            code='partners_intervention_signed_pd',
            content_object=intervention,
        )
        intervention.unicef_focal_points.add(UserFactory())
        intervention.sections.add(SectionFactory())
        intervention.offices.add(OfficeFactory())
        intervention.partner_focal_points.add(PartnerStaffFactory())

        attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'prc_review_attachment': attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
