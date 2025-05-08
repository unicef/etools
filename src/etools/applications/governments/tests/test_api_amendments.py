import datetime
from unittest import mock

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone, translation

from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.governments.models import GDD, GDDAmendment
from etools.applications.governments.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.governments.tests.factories import (
    GDDAmendmentFactory,
    GDDFactory,
    GDDReportingRequirementFactory,
    GDDReviewFactory,
    PartnerFactory,
)
from etools.applications.partners.tests.factories import AgreementFactory
from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class BaseTestGDDAmendments:
    # test basic api flow
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('update_notifications')

    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])
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
        self.active_gdd = GDDFactory(
            agreement=self.active_agreement,
            title='Active GDD',
            start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=90),
            status=GDD.ACTIVE,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            unicef_signatory=self.unicef_staff,
            partner_authorized_officer_signatory=self.partner.active_staff_members.all().first(),
            budget_owner=self.pme,
        )
        self.active_gdd.flat_locations.add(LocationFactory())
        self.active_gdd.partner_focal_points.add(self.partner_staff)
        self.active_gdd.unicef_focal_points.add(self.unicef_staff)
        self.active_gdd.offices.add(OfficeFactory())
        self.active_gdd.sections.add(SectionFactory())
        GDDReportingRequirementFactory(gdd=self.active_gdd)


class TestGDDAmendments(BaseTestGDDAmendments, BaseTenantTestCase):
    fixtures = ('groups',)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
            UserFactory(), data={}, request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        self.user = None
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
            None, data={}, request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_partnership_member(self):
        """Ensure group membership is sufficient for create"""
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
            UserFactory(is_staff=True), data={}, request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_amendment_invalid_type(self):
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': ['invalid_choice'],
                'kind': GDDAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['types'],
                         {0: [ErrorDetail(string='"invalid_choice" is not a valid choice.', code='invalid_choice')]})

    def test_create_amendment_other_type_no_description(self):
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [GDDAmendment.OTHER],
                'kind': GDDAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['non_field_errors'], [ErrorDetail(
                string="Other description required, if type 'Other' selected.",
                code='invalid'
            )]
        )

    def test_create_amendment_not_unique_error_translated(self):
        GDDAmendmentFactory(
            gdd=self.active_gdd, kind=GDDAmendment.KIND_NORMAL,
        )
        with translation.override('fr'):
            response = self.forced_auth_req(
                'post',
                reverse('governments:gdd-amendments-list', args=[self.active_gdd.pk]),
                UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
                data={
                    'types': [GDDAmendment.TYPE_CHANGE],
                    'kind': GDDAmendment.KIND_NORMAL,
                },
                request_format='multipart',
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['non_field_errors'][0],
            "On ne peut pas ajouter un nouvel amendement alors qu'un autre amendement du même type est en cours."
        )

    def test_start_amendment(self):
        gdd = GDDFactory()
        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[gdd.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [GDDAmendment.TYPE_CHANGE],
                'kind': GDDAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[gdd.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [GDDAmendment.TYPE_CHANGE],
                'kind': GDDAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.forced_auth_req(
            'post',
            reverse('governments:gdd-amendments-list', args=[gdd.pk]),
            UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'types': [GDDAmendment.TYPE_CHANGE],
                'kind': GDDAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_permissions_fields_hidden(self):
        amendment = GDDAmendmentFactory(gdd=self.active_gdd)
        response = self.forced_auth_req(
            'get', reverse('governments:gdd-detail', args=[amendment.amended_gdd.pk]), self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['partner_focal_points'])
        self.assertFalse(response.data['permissions']['edit']['partner_focal_points'])
        self.assertFalse(response.data['permissions']['view']['unicef_focal_points'])
        self.assertTrue(response.data['permissions']['edit']['unicef_focal_points'])
        self.assertFalse(response.data['permissions']['view']['planned_visits'])
        self.assertFalse(response.data['permissions']['edit']['planned_visits'])
        self.assertFalse(response.data['permissions']['view']['frs'])
        self.assertFalse(response.data['permissions']['edit']['frs'])
        self.assertFalse(response.data['permissions']['view']['attachments'])
        self.assertFalse(response.data['permissions']['edit']['attachments'])

    def test_geographical_coverage_sites_ignored_in_difference(self):
        location = LocationFactory()
        site = LocationSiteFactory()
        amendment = GDDAmendmentFactory(gdd=self.active_gdd)
        amendment.amended_gdd.flat_locations.add(location)
        amendment.amended_gdd.sites.add(site)

        difference = amendment.get_difference()
        self.assertIn('flat_locations', difference)
        self.assertNotIn('sites', difference)

    def test_geographical_coverage_not_available(self):
        amendment = GDDAmendmentFactory(gdd=self.active_gdd)
        response = self.forced_auth_req(
            'get', reverse('governments:gdd-detail', args=[amendment.amended_gdd.pk]), self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['sites'])
        self.assertFalse(response.data['permissions']['edit']['sites'])

        original_gdd_response = self.forced_auth_req(
            'get', reverse('governments:gdd-detail', args=[amendment.gdd.pk]), self.unicef_staff
        )
        self.assertEqual(original_gdd_response.status_code, status.HTTP_200_OK)
        self.assertTrue(original_gdd_response.data['permissions']['view']['sites'])
        self.assertTrue(original_gdd_response.data['permissions']['edit']['sites'])

    def test_currency_not_editable_in_amendment(self):
        amendment = GDDAmendmentFactory(gdd=self.active_gdd)
        gpd = amendment.amended_gdd
        response = self.forced_auth_req(
            'get',
            reverse('governments:gdd-detail', args=[gpd.pk]),
            self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # view and no edit rights when in amendment
        self.assertTrue(response.data['permissions']['view']['document_currency'])
        self.assertFalse(response.data['permissions']['edit']['document_currency'])

        self.assertEqual(amendment.amended_gdd.document_currency, 'USD')
        response = self.forced_auth_req(
            'patch',
            reverse('governments:gdd-detail', args=[gpd.pk]),
            self.unicef_staff,
            data={"document_currency": "RON"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gpd.refresh_from_db()
        self.assertEqual(gpd.document_currency, 'USD')


class TestGDDAmendmentDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.gdd = GDDFactory(status=GDD.DRAFT)

    def setUp(self):
        super().setUp()
        self.amendment = GDDAmendmentFactory(
            gdd=self.gdd,
            types=[GDDAmendment.RESULTS],
        )
        self.url = reverse(
            "governments:gdd-amendments-del",
            args=[self.amendment.pk]
        )

    def test_delete(self):
        self.gdd.unicef_focal_points.add(self.unicef_staff)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GDDAmendment.objects.filter(pk=self.amendment.pk).exists())
        self.assertFalse(GDD.objects.filter(pk=self.amendment.amended_gdd.pk).exists())

    def test_delete_inactive(self):
        self.gdd.unicef_focal_points.add(self.unicef_staff)
        self.amendment.is_active = False
        self.amendment.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_gdd_amendments_delete(self):
        last_gdd_amendment = GDDAmendment.objects.all().last()
        inexistent_id = last_gdd_amendment.id + 1000

        response = self.forced_auth_req(
            'delete',
            reverse("governments:gdd-amendments-del", args=[inexistent_id]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_active(self):
        self.gdd.unicef_focal_points.add(self.unicef_staff)
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


class TestGDDAmendmentsMerge(BaseTestGDDAmendments, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.amendment = GDDAmendmentFactory(gdd=self.active_gdd, types=[GDDAmendment.TYPE_ADMIN_ERROR])
        self.amended_gdd = self.amendment.amended_gdd
        response = self.forced_auth_req(
            'patch',
            reverse('governments:gdd-detail', args=[self.amended_gdd.pk]),
            self.unicef_staff,
            data={
                'start': timezone.now().date() + datetime.timedelta(days=2),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.amended_gdd.refresh_from_db()
        self.assertEqual(self.amended_gdd.start, timezone.now().date() + datetime.timedelta(days=2))

        self.amended_gdd.unicef_accepted = True
        self.amended_gdd.partner_accepted = True
        self.amended_gdd.date_sent_to_partner = timezone.now().date()
        self.amended_gdd.save()
        review = GDDReviewFactory(
            gdd=self.amended_gdd, overall_approval=True,
            overall_approver=UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            authorized_officer=UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
        )
        response = self.forced_auth_req(
            'patch',
            reverse('governments:gdd-signature', args=[self.amended_gdd.pk]),
            review.authorized_officer,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.amended_gdd.refresh_from_db()
        self.assertEqual('approved', response.data['status'])

    @mock.patch("etools.applications.governments.tasks.send_gdd_to_vision.delay")
    def test_amend_gdd_budget_owner(self, send_to_vision_mock):
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            response = self.forced_auth_req(
                'patch',
                reverse('governments:gdd-amendment-merge', args=[self.amended_gdd.pk]),
                self.unicef_staff,
                data={}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['id'], self.active_gdd.id)

        self.active_gdd.refresh_from_db()
        self.assertEqual(self.active_gdd.start, timezone.now().date() + datetime.timedelta(days=2))
        send_to_vision_mock.assert_called()
        self.assertEqual(len(commit_callbacks), 1)

    def test_amend_gdd_focal_point(self):
        response = self.forced_auth_req(
            'patch',
            reverse('governments:gdd-amendment-merge', args=[self.amended_gdd.pk]),
            self.unicef_staff,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.active_gdd.refresh_from_db()
        self.assertEqual(self.active_gdd.start, timezone.now().date() + datetime.timedelta(days=2))
        self.assertEqual(self.active_gdd.amendments.count(), 1)
        self.assertEqual(self.amendment.signed_date, timezone.now().date())

    def test_merge_error(self):
        first_amendment = GDDAmendmentFactory(
            gdd=self.active_gdd, kind=GDDAmendment.KIND_NORMAL,
        )
        second_amendment = GDDAmendmentFactory(
            gdd=self.active_gdd, kind=GDDAmendment.KIND_CONTINGENCY,
        )
        second_amendment.amended_gdd.start = timezone.now().date() - datetime.timedelta(days=15)
        second_amendment.amended_gdd.save()
        second_amendment.merge_amendment()

        first_amendment.amended_gdd.start = timezone.now().date() - datetime.timedelta(days=14)
        first_amendment.amended_gdd.status = GDD.APPROVED
        first_amendment.amended_gdd.save()

        response = self.forced_auth_req(
            'patch',
            reverse('governments:gdd-amendment-merge', args=[first_amendment.amended_gdd.pk]),
            self.unicef_staff,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Merge Error', response.data[0])
