import datetime
from unittest import mock, skip
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone, translation

from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.partners.models import Intervention, InterventionAmendment
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionReviewFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
)
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class BaseTestInterventionAmendments:
    # test basic api flow
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('update_notifications')

    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True)
        self.pme = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])

        self.partner = PartnerFactory()
        self.partner_staff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.partner.organization
        )

        year_ago = datetime.date.today() - datetime.timedelta(days=365)
        self.active_agreement = AgreementFactory(
            partner=self.partner,
            status='active',
            signed_by_unicef_date=year_ago,
            signed_by_partner_date=year_ago,
            start=year_ago,
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
            partner_authorized_officer_signatory=self.partner.active_staff_members.all().first(),
            budget_owner=self.pme,
        )
        self.active_intervention.flat_locations.add(LocationFactory())
        self.active_intervention.partner_focal_points.add(self.partner_staff)
        self.active_intervention.unicef_focal_points.add(self.unicef_staff)
        self.active_intervention.offices.add(OfficeFactory())
        self.active_intervention.sections.add(SectionFactory())
        ReportingRequirementFactory(intervention=self.active_intervention)


class TestInterventionAmendments(BaseTestInterventionAmendments, BaseTenantTestCase):
    def test_no_permission_user_forbidden(self):
        '''Ensure a non-staff user gets the 403 smackdown'''
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(), data={}, request_format='multipart',
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        '''Ensure an unauthenticated user gets the 403 smackdown'''
        self.user = None
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            None, data={}, request_format='multipart',
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_partnership_member(self):
        '''Ensure group membership is sufficient for create;'''
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(is_staff=True), data={}, request_format='multipart',
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_amendment_invalid_type(self):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': ['invalid_choice'],
                'kind': InterventionAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data['types'],
                          {0: [ErrorDetail(string='"invalid_choice" is not a valid choice.', code='invalid_choice')]})

    def test_create_amendment_other_type_no_description(self):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.OTHER],
                'kind': InterventionAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.data['non_field_errors'], [ErrorDetail(
                string="Other description required, if type 'Other' selected.",
                code='invalid'
            )]
        )

    @skip("todo: save implement prc review process on merge")
    def test_create_amendment_with_internal_prc_review(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        flat_qs = AttachmentFlat.objects.filter(attachment=attachment)
        assert flat_qs.exists()
        flat = flat_qs.first()
        assert not flat.partner
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_NORMAL,
                'internal_prc_review': attachment.pk,
            },
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['intervention'], self.active_intervention.pk)
        attachment.refresh_from_db()
        self.assertEqual(
            attachment.file_type.code,
            "partners_intervention_amendment_internal_prc_review"
        )
        self.assertEqual(attachment.object_id, response.data["id"])
        self.assertEqual(
            attachment.code,
            "partners_intervention_amendment_internal_prc_review"
        )

        # check denormalization
        flat = flat_qs.first()
        assert flat.partner
        assert flat.pd_ssfa
        assert flat.pd_ssfa_number

    @patch("etools.applications.partners.utils.send_notification_with_template")
    def test_create_amendment_with_internal_prc_review_none(self, mock_send):
        ts = TenantSwitchFactory(name="intervention_amendment_notifications_on", countries=[connection.tenant])
        self.assertTrue(ts.is_active)

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )
        self.assertEqual(mock_send.call_count, 1)
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['intervention'], self.active_intervention.pk)

    def test_create_amendment_not_unique_error_translated(self):
        InterventionAmendmentFactory(
            intervention=self.active_intervention, kind=InterventionAmendment.KIND_NORMAL,
        )
        with translation.override('fr'):
            response = self.forced_auth_req(
                'post',
                reverse('partners_api:intervention-amendments-add', args=[self.active_intervention.pk]),
                UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
                data={
                    'types': [InterventionAmendment.TYPE_CHANGE],
                    'kind': InterventionAmendment.KIND_NORMAL,
                },
                request_format='multipart',
            )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['non_field_errors'][0],
            "On ne peut pas ajouter un nouvel amendement alors qu'un autre amendement du même type est en cours."
        )

    def test_start_amendment(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
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
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
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
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'kind': InterventionAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_permissions_fields_hidden(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[amendment.amended_intervention.pk]), self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['partner_focal_points'])
        self.assertFalse(response.data['permissions']['edit']['partner_focal_points'])
        self.assertFalse(response.data['permissions']['view']['unicef_focal_points'])
        self.assertFalse(response.data['permissions']['edit']['unicef_focal_points'])
        self.assertFalse(response.data['permissions']['view']['planned_visits'])
        self.assertFalse(response.data['permissions']['edit']['planned_visits'])
        self.assertFalse(response.data['permissions']['view']['frs'])
        self.assertFalse(response.data['permissions']['edit']['frs'])
        self.assertFalse(response.data['permissions']['view']['attachments'])
        self.assertFalse(response.data['permissions']['edit']['attachments'])

    def test_amendment_prc_no_review_type(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amendment.amended_intervention.unicef_accepted = True
        amendment.amended_intervention.partner_accepted = True
        amendment.amended_intervention.date_sent_to_partner = timezone.now().date()
        amendment.amended_intervention.save()
        InterventionSupplyItemFactory(intervention=amendment.amended_intervention)

        self.assertEqual({}, amendment.difference)
        response = self.forced_auth_req(
            "patch", reverse('pmp_v3:intervention-review', args=[amendment.amended_intervention.pk]),
            user=self.unicef_staff, data={'review_type': 'no-review'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        amendment.amended_intervention.refresh_from_db()
        self.assertEqual(amendment.amended_intervention.status, Intervention.SIGNATURE)

        # check difference updated on review
        amendment.refresh_from_db()
        self.assertNotEqual({}, amendment.difference)

    def test_amendment_review_original_budget_changed(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amendment.amended_intervention.unicef_accepted = True
        amendment.amended_intervention.partner_accepted = True
        amendment.amended_intervention.date_sent_to_partner = timezone.now().date()
        amendment.amended_intervention.save()
        amendment.amended_intervention.planned_budget.total_hq_cash_local += 2
        amendment.amended_intervention.planned_budget.save()

        self.active_intervention.planned_budget.total_hq_cash_local += 1
        self.active_intervention.planned_budget.save()

        response = self.forced_auth_req(
            "patch", reverse('pmp_v3:intervention-review', args=[amendment.amended_intervention.pk]),
            user=self.unicef_staff, data={'review_type': 'no-review'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_hq_cash_local', response.data[0])

    @override_settings(PMP_V2_RELEASE_DATE=datetime.date(year=2020, month=10, day=1))
    def test_amendment_review_pd_v1(self):
        self.active_intervention.start = datetime.date(year=2019, month=10, day=1)
        self.active_intervention.budget_owner = None
        self.active_intervention.date_sent_to_partner = None
        self.active_intervention.save()

        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amendment.amended_intervention.budget_owner = self.unicef_staff
        amendment.amended_intervention.unicef_accepted = True
        amendment.amended_intervention.partner_accepted = True
        amendment.amended_intervention.save()

        response = self.forced_auth_req(
            "patch", reverse('pmp_v3:intervention-review', args=[amendment.amended_intervention.pk]),
            user=self.unicef_staff, data={'review_type': 'no-review'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], Intervention.SIGNATURE)

    def test_geographical_coverage_sites_ignored_in_difference(self):
        location = LocationFactory()
        site = LocationSiteFactory()
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amendment.amended_intervention.flat_locations.add(location)
        amendment.amended_intervention.sites.add(site)

        difference = amendment.get_difference()
        self.assertIn('flat_locations', difference)
        self.assertNotIn('sites', difference)

    def test_geographical_coverage_not_available(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[amendment.amended_intervention.pk]), self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['sites'])
        self.assertFalse(response.data['permissions']['edit']['sites'])

        original_intervention_response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[amendment.intervention.pk]), self.unicef_staff
        )
        self.assertEqual(original_intervention_response.status_code, status.HTTP_200_OK)
        self.assertTrue(original_intervention_response.data['permissions']['view']['sites'])
        self.assertTrue(original_intervention_response.data['permissions']['edit']['sites'])


class TestInterventionAmendmentDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory(status=Intervention.DRAFT)

    def setUp(self):
        super().setUp()
        self.amendment = InterventionAmendmentFactory(
            intervention=self.intervention,
            types=[InterventionAmendment.RESULTS],
        )
        self.url = reverse(
            "partners_api:intervention-amendments-del",
            args=[self.amendment.pk]
        )

    def test_delete(self):
        self.intervention.unicef_focal_points.add(self.unicef_staff)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InterventionAmendment.objects.filter(pk=self.amendment.pk).exists())
        self.assertFalse(Intervention.objects.filter(pk=self.amendment.amended_intervention.pk).exists())

    def test_delete_inactive(self):
        self.intervention.unicef_focal_points.add(self.unicef_staff)
        self.amendment.is_active = False
        self.amendment.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_intervention_amendments_delete(self):
        last_intervention_amendment = InterventionAmendment.objects.all().last()
        inexistent_id = last_intervention_amendment.id + 1000

        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-amendments-del", args=[inexistent_id]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_active(self):
        self.intervention.unicef_focal_points.add(self.unicef_staff)
        self.amendment.is_active = True
        self.amendment.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_active_partnership_manager(self):
        self.amendment.is_active = True
        self.amendment.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestInterventionAmendmentsMerge(BaseTestInterventionAmendments, BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        country_programme = CountryProgrammeFactory()
        self.intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=UserFactory(
                profile__organization=self.partner.organization,
                user__is_staff=False, realms__data=['IP Viewer']
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
        self.intervention.flat_locations.add(LocationFactory())
        self.intervention.planned_budget.total_hq_cash_local = 10
        self.intervention.planned_budget.save()
        # FundsReservationHeaderFactory(intervention=intervention, currency='USD') # frs code is unique
        ReportingRequirementFactory(intervention=self.intervention)
        self.unicef_focal_point = UserFactory(is_staff=True)
        self.intervention.unicef_focal_points.add(self.unicef_focal_point)
        self.intervention.sections.add(SectionFactory())
        self.intervention.offices.add(OfficeFactory())
        self.intervention.partner_focal_points.add(UserFactory(
            profile__organization=self.partner.organization,
            user__is_staff=False, realms__data=['IP Viewer']
        ))
        ReportingRequirementFactory(intervention=self.intervention)

        amendment = InterventionAmendment.objects.create(
            intervention=self.intervention,
            types=[InterventionAmendment.TYPE_ADMIN_ERROR],
        )
        self.amended_intervention = amendment.amended_intervention

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.amended_intervention.pk]),
            self.unicef_focal_point,
            data={
                'start': timezone.now().date() + datetime.timedelta(days=2),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.amended_intervention.refresh_from_db()
        self.assertEqual(self.amended_intervention.start, timezone.now().date() + datetime.timedelta(days=2))

        self.amended_intervention.unicef_accepted = True
        self.amended_intervention.partner_accepted = True
        self.amended_intervention.date_sent_to_partner = timezone.now().date()
        self.amended_intervention.status = Intervention.REVIEW
        self.amended_intervention.save()
        review = InterventionReviewFactory(
            intervention=self.amended_intervention, overall_approval=True,
            overall_approver=UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
        )

        # sign amended intervention
        self.amended_intervention.signed_by_partner_date = self.intervention.signed_by_partner_date
        self.amended_intervention.signed_by_unicef_date = self.intervention.signed_by_unicef_date
        self.amended_intervention.partner_authorized_officer_signatory = self.intervention.partner_authorized_officer_signatory
        self.amended_intervention.unicef_signatory = self.intervention.unicef_signatory
        self.amended_intervention.save()
        AttachmentFactory(
            code='partners_intervention_signed_pd',
            file='sample1.pdf',
            content_object=self.amended_intervention
        )

        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.start, timezone.now().date() + datetime.timedelta(days=1))

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-signature', args=[self.amended_intervention.pk]),
            review.overall_approver,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.amended_intervention.refresh_from_db()
        self.assertEqual('signed', response.data['status'])

    @mock.patch("etools.applications.partners.tasks.send_pd_to_vision.delay")
    def test_amend_intervention_budget_owner(self, send_to_vision_mock):
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            response = self.forced_auth_req(
                'patch',
                reverse('pmp_v3:intervention-amendment-merge', args=[self.amended_intervention.pk]),
                self.intervention.budget_owner,
                data={}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['id'], self.intervention.id)

        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.start, timezone.now().date() + datetime.timedelta(days=2))
        send_to_vision_mock.assert_called()
        self.assertEqual(len(commit_callbacks), 1)

    def test_amend_intervention_focal_point(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-amendment-merge', args=[self.amended_intervention.pk]),
            self.unicef_focal_point,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_merge_error(self):
        first_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention, kind=InterventionAmendment.KIND_NORMAL,
        )
        second_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention, kind=InterventionAmendment.KIND_CONTINGENCY,
        )
        second_amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=15)
        second_amendment.amended_intervention.save()
        second_amendment.merge_amendment()

        first_amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=14)
        first_amendment.amended_intervention.status = Intervention.SIGNED
        first_amendment.amended_intervention.save()

        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-amendment-merge', args=[first_amendment.amended_intervention.pk]),
            self.active_intervention.budget_owner,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Merge Error', response.data[0])
