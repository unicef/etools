from datetime import date
from unittest import skip
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from factory import fuzzy

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import FileType, Intervention, InterventionRisk, InterventionAmendment
from etools.applications.partners.tests.factories import (
    FileTypeFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    InterventionRiskFactory,
    PartnerFactory,
    PartnerStaffFactory, InterventionPlannedVisitsFactory, InterventionAmendmentFactory,
)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.unicef_user = UserFactory(is_staff=True, groups__data=['UNICEF User'])
        self.partnership_manager = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])

        self.partner = PartnerFactory(vendor_number=fuzzy.FuzzyText(length=20).fuzz())
        self.partner_staff_member = UserFactory(is_staff=False, groups__data=[])
        self.partner_staff_member.profile.partner_staff_member = PartnerStaffFactory(
            partner=self.partner, email=self.partner_staff_member.email
        ).id
        self.partner_staff_member.profile.save()

        self.partner_authorized_officer = UserFactory(is_staff=False, groups__data=[])
        partner_authorized_officer_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_authorized_officer.email
        )
        self.partner_authorized_officer.profile.partner_staff_member_user = partner_authorized_officer_staff.id
        self.partner_authorized_officer.profile.save()

        self.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        partner_focal_point_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_focal_point.email
        )
        self.partner_focal_point.profile.partner_staff_member = partner_focal_point_staff.id
        self.partner_focal_point.profile.save()

        self.draft_intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
        )
        self.draft_intervention.unicef_focal_points.add(UserFactory())
        self.draft_intervention.partner_focal_points.add(partner_focal_point_staff)

        country_programme = CountryProgrammeFactory()
        self.ended_intervention = InterventionFactory(
            agreement__partner=self.partner,
            status=Intervention.ENDED,
            signed_by_partner_date=date(year=1970, month=1, day=1),
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
            signed_by_unicef_date=date(year=1970, month=1, day=1),
            country_programme=country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            agreement__country_programme=country_programme,
        )
        FundsReservationHeaderFactory(intervention=self.ended_intervention)
        InterventionBudgetFactory(intervention=self.ended_intervention, unicef_cash_local=1)
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_ended_pd',
            content_object=self.ended_intervention,
        )
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.ended_intervention,
        )
        self.ended_intervention.unicef_focal_points.add(UserFactory())
        self.ended_intervention.sections.add(SectionFactory())
        self.ended_intervention.offices.add(OfficeFactory())
        self.ended_intervention.partner_focal_points.add(partner_focal_point_staff)


class TestRisksManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partnership_manager_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partnership_manager_ended_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], True)

    # check functionality
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
            reverse('pmp_v3:intervention-risk-delete', args=[self.draft_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.risks.count(), 0)

    # check permissions matrix is honored; editable only in draft
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
            reverse('pmp_v3:intervention-risk-delete', args=[self.ended_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # check partner has no access
    def test_add_as_partner_user(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data[0], 'Cannot change fields while in draft: risks')

    def test_add_as_partner_user_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        self.assertEqual(self.draft_intervention.risks.count(), 0)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['risks'][0]['risk_type'], InterventionRisk.RISK_TYPE_FINANCIAL)
        self.assertEqual(self.draft_intervention.risks.count(), 1)


class TestProgrammaticVisitsManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)

    def test_partner_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], False)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)
        self.assertNotIn('planned_visits', response.data)

    # test functionality
    def test_add(self):
        self.assertEqual(self.draft_intervention.planned_visits.count(), 0)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'planned_visits': [{
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)
        self.assertEqual(self.draft_intervention.planned_visits.count(), 1)

    def test_update(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'planned_visits': [{
                    'id': visit.id,
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_destroy(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:interventions-planned-visits-delete', args=[self.draft_intervention.pk, visit.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.planned_visits.count(), 0)

    @skip("planned visits are editable for all intervention statuses at this moment")
    def test_add_for_ended_intervention(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'planned_visits': [{
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in ended: planned_visits', response.data[0])

    @skip("planned visits are editable for all intervention statuses at this moment")
    def test_destroy_for_ended_intervention(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:interventions-planned-visits-delete', args=[self.ended_intervention.pk, visit.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestFinancialManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], True)

    # todo: there is no field for headquarter contribution percent
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
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], True)
        self.assertEqual(response.data['permissions']['edit']['frs'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], True)
        self.assertEqual(response.data['permissions']['edit']['frs'], True)

    def test_partner_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], False)
        self.assertEqual(response.data['permissions']['edit']['frs'], False)
        self.assertNotIn('frs', response.data)

    # test functionality
    @patch('etools.applications.funds.views.sync_single_delegated_fr')
    def test_sync(self, sync_mock):
        def generate_frs(business_area_code, fr_number):
            FundsReservationHeaderFactory(
                fr_number=fr_number,
                intervention=self.draft_intervention,
                vendor_code=self.partner.vendor_number,
            )

        sync_mock.side_effect = generate_frs

        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partnership_manager,
            data={
                'intervention': self.draft_intervention.id,
                'values': 'test',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_sync_existing(self):
        frs = FundsReservationHeaderFactory(
            intervention=self.draft_intervention,
            vendor_code=self.partner.vendor_number,
        )
        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partnership_manager,
            data={
                'intervention': self.draft_intervention.id,
                'values': frs.fr_number,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_sync_for_partner(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partner_focal_point,
            data={
                'intervention': self.draft_intervention.id,
                'values': 'test',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)


class TestSignedDocumentsManagement(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.data = {
            'submission_date': '1970-01-01',
            'submission_date_prc': '1970-01-01',
            'review_date_prc': '1970-01-01',
            'prc_review_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
            'signed_by_unicef_date': '1970-01-02',
            'signed_by_partner_date': '1970-01-02',
            'unicef_signatory': UserFactory().id,
            'partner_authorized_officer_signatory': PartnerStaffFactory(partner=self.partner).pk,
            'signed_pd_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }

    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

    # test functionality
    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data=self.data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for field in self.data.keys():
            self.assertEqual(response.data['permissions']['edit'][field], True, field)
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
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', b'hello world!'),
        )

    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], True)

    # test functionality
    def test_add(self):
        self.assertEqual(self.draft_intervention.amendments.count(), 0)
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'types': [InterventionAmendment.OTHER],
                'other_description': 'test',
                'signed_amendment_attachment': self.example_attachment.pk,
                'signed_date': '1970-01-01',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.draft_intervention.amendments.count(), 1)

    def test_update(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

    def test_destroy(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.amendments.count(), 0)

    def test_add_for_ended_intervention(self):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'types': [InterventionAmendment.OTHER],
                'other_description': 'test',
                'signed_amendment_attachment': self.example_attachment.pk,
                'signed_date': '1970-01-01',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_for_ended_intervention(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestFinalPartnershipReviewManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        FileTypeFactory(name=FileType.FINAL_PARTNERSHIP_REVIEW)
        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', b'hello world!'),
        )

    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], True)

    # test functionality
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
