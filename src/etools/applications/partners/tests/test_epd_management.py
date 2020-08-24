from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import FileType, Intervention, InterventionRisk
from etools.applications.partners.tests.factories import (
    FileTypeFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    InterventionRiskFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.partnership_manager = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])

        cls.partner = PartnerFactory()
        cls.draft_intervention = InterventionFactory(agreement__partner=cls.partner)

        country_programme = CountryProgrammeFactory()
        cls.ended_intervention = InterventionFactory(
            agreement__partner=cls.partner,
            status=Intervention.ENDED,
            signed_by_partner_date=date(year=1970, month=1, day=1),
            partner_authorized_officer_signatory=PartnerStaffFactory(partner=cls.partner),
            signed_by_unicef_date=date(year=1970, month=1, day=1),
            country_programme=country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            agreement__country_programme=country_programme,
        )
        FundsReservationHeaderFactory(intervention=cls.ended_intervention)
        InterventionBudgetFactory(intervention=cls.ended_intervention, unicef_cash_local=1)
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_ended_pd',
            content_object=cls.ended_intervention,
        )
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=cls.ended_intervention,
        )
        cls.ended_intervention.unicef_focal_points.add(UserFactory())
        cls.ended_intervention.sections.add(SectionFactory())
        cls.ended_intervention.offices.add(OfficeFactory())
        cls.ended_intervention.partner_focal_points.add(PartnerStaffFactory())


class TestRisksManagement(BaseTestCase):
    def test_add(self):
        self.assertEqual(self.draft_intervention.risks.count(), 0)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['risks'], True)
        self.assertEqual(response.data['risks'][0]['risk_type'], InterventionRisk.RISK_TYPE_FINANCIAL)
        self.assertEqual(self.draft_intervention.risks.count(), 1)

    def test_update(self):
        risk = InterventionRiskFactory(
            intervention=self.draft_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{
                    'id': risk.id, 'risk_type': InterventionRisk.RISK_TYPE_OPERATIONAL
                }],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['risks'][0]['risk_type'], InterventionRisk.RISK_TYPE_OPERATIONAL)

    def test_destroy(self):
        risk = InterventionRiskFactory(
            intervention=self.draft_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-risk-detail', args=[self.draft_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.risks.count(), 0)

    def test_add_for_ended_intervention(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in ended: risks', response.data[0])

    def test_destroy_for_ended_intervention(self):
        risk = InterventionRiskFactory(
            intervention=self.ended_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-risk-detail', args=[self.ended_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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

    def test_update_ended(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': Intervention.CASH_TRANSFER_PAYMENT,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in ended: cash_transfer_modalities', response.data[0])


class TestFundsReservationManagement(BaseTestCase):
    pass


class TestSignedDocumentsManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.data = {
            'submission_date': '1970-01-01',
            'submission_date_prc': '1970-01-01',
            'review_date_prc': '1970-01-01',
            'prc_review_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
            'signed_by_unicef_date': '1970-01-02',
            'signed_by_partner_date': '1970-01-02',
            'unicef_signatory': UserFactory().id,
            'partner_authorized_officer_signatory': PartnerStaffFactory(partner=cls.partner).pk,
            'signed_pd_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }

    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data=self.data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['edit'][field], True)
            self.assertIsNotNone(response.data[field], f'{field} is unexpectedly None')

    def test_update_ended(self):
        # check in loop because there are only one error will be raised at a moment
        for field, value in self.data.items():
            response = self.forced_auth_req(
                'patch',
                reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
                user=self.partnership_manager,
                data={field: value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, f'wrong response for {field}')
            self.assertEqual(f'Cannot change fields while in ended: {field}', response.data[0])


class TestAmendmentsManagement(BaseTestCase):
    pass


class TestFinalPartnershipReviewManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        FileTypeFactory(name=FileType.FINAL_PARTNERSHIP_REVIEW)
        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', b'hello world!'),
        )

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
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'final_partnership_review': self.example_attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'Cannot change fields while in ended: final_partnership_review')
