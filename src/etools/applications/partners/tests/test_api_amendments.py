import datetime

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention, InterventionAmendment
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionReviewFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestInterventionAmendments(BaseTenantTestCase):
    # test basic api flow
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('update_notifications')

    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        self.pme = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])

        self.partner = PartnerFactory(name='Partner')
        self.active_agreement = AgreementFactory(
            partner=self.partner,
            status='active',
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today()
        )

        self.active_intervention = InterventionFactory(
            agreement=self.active_agreement,
            title='Active Intervention',
            document_type=Intervention.PD,
            start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=90),
            status=Intervention.ACTIVE,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=self.unicef_staff,
            partner_authorized_officer_signatory=self.partner.staff_members.all().first()
        )
        ReportingRequirementFactory(intervention=self.active_intervention)

    def test_start_amendment(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_amend_intervention(self):
        country_programme = CountryProgrammeFactory()
        intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=PartnerStaffFactory(
                partner=self.partner, user__is_staff=False, user__groups__data=[]
            ),
            unicef_signatory=UserFactory(),
            country_programme=country_programme,
            submission_date=timezone.now().date(),
            start=timezone.now().date() + datetime.timedelta(days=1),
            end=timezone.now().date() + datetime.timedelta(days=30),
            date_sent_to_partner=timezone.now().date(),
            signed_by_unicef_date=timezone.now().date(),
            signed_by_partner_date=timezone.now().date(),
            agreement__country_programme=country_programme,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            budget_owner=UserFactory(),
            contingency_pd=False,
            unicef_court=True,
        )
        intervention.planned_budget.total_hq_cash_local = 10
        intervention.planned_budget.save()
        # FundsReservationHeaderFactory(intervention=intervention, currency="USD") # frs code is unique
        ReportingRequirementFactory(intervention=intervention)
        intervention.unicef_focal_points.add(UserFactory())
        intervention.sections.add(SectionFactory())
        intervention.offices.add(OfficeFactory())
        intervention.partner_focal_points.add(PartnerStaffFactory(
            partner=self.partner, user__is_staff=False, user__groups__data=[]
        ))
        ReportingRequirementFactory(intervention=intervention)

        amendment = InterventionAmendment.objects.create(
            intervention=intervention,
            types=[InterventionAmendment.TYPE_ADMIN_ERROR],
        )
        amended_intervention = amendment.amended_intervention

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[amended_intervention.pk]),
            UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'start': timezone.now().date() + datetime.timedelta(days=2),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        amended_intervention.refresh_from_db()
        self.assertEqual(amended_intervention.start, timezone.now().date() + datetime.timedelta(days=2))

        amended_intervention.unicef_accepted = True
        amended_intervention.partner_accepted = True
        amended_intervention.status = Intervention.REVIEW
        amended_intervention.save()
        InterventionReviewFactory(intervention=amended_intervention, overall_approval=True)

        # sign amended intervention
        amended_intervention.signed_by_partner_date = intervention.signed_by_partner_date
        amended_intervention.signed_by_unicef_date = intervention.signed_by_unicef_date
        amended_intervention.partner_authorized_officer_signatory = intervention.partner_authorized_officer_signatory
        amended_intervention.unicef_signatory = intervention.unicef_signatory
        amended_intervention.save()
        AttachmentFactory(
            code='partners_intervention_signed_pd',
            file="sample1.pdf",
            content_object=amended_intervention
        )

        intervention.refresh_from_db()
        self.assertEqual(intervention.start, timezone.now().date() + datetime.timedelta(days=1))

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-signature', args=[amended_intervention.pk]),
            UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        amended_intervention.refresh_from_db()
        self.assertEqual('signed', response.data['status'])

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-amendment-merge', args=[amended_intervention.pk]),
            intervention.budget_owner,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['id'], intervention.id)

        intervention.refresh_from_db()
        self.assertEqual(intervention.start, timezone.now().date() + datetime.timedelta(days=2))

    def test_permissions_fields_hidden(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        response = self.forced_auth_req('get', reverse('pmp_v3:intervention-detail', args=[amendment.amended_intervention.pk]), self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['partner_focal_points'])
        self.assertFalse(response.data['permissions']['view']['unicef_focal_points'])
        self.assertFalse(response.data['permissions']['view']['planned_visits'])
        self.assertFalse(response.data['permissions']['view']['frs'])
        self.assertFalse(response.data['permissions']['view']['attachments'])