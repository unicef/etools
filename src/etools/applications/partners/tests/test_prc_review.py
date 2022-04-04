import itertools
from datetime import date
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from factory import fuzzy
from rest_framework import status
from unicef_snapshot.models import Activity

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PRC_SECRETARY, UNICEF_USER
from etools.applications.partners.tests.factories import (
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


class BaseInterventionMixin:
    def setUp(self):
        super().setUp()
        self.country_programme = CountryProgrammeFactory()
        self.partner = PartnerFactory(vendor_number=fuzzy.FuzzyText(length=20).fuzz())
        self.partner_authorized_officer = UserFactory(is_staff=False, groups__data=[])
        self.partner_authorized_officer_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_authorized_officer.email, user=self.partner_authorized_officer
        )
        self.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        self.partner_focal_point_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_focal_point.email, user=self.partner_focal_point
        )


class DevelopInterventionMixin(BaseInterventionMixin):
    def setUp(self):
        super().setUp()
        self.develop_intervention = InterventionFactory(
            agreement__partner=self.partner,
            status=Intervention.DRAFT,
            partner_authorized_officer_signatory=self.partner_authorized_officer_staff,
            country_programme=self.country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            agreement__country_programme=self.country_programme,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            budget_owner=UserFactory(),
        )
        self.develop_intervention.partner_focal_points.add(self.partner_focal_point_staff)


class ReviewInterventionMixin(BaseInterventionMixin):
    def setUp(self):
        super().setUp()
        self.review_intervention = InterventionFactory(
            agreement__partner=self.partner,
            status=Intervention.REVIEW,
            partner_authorized_officer_signatory=self.partner_authorized_officer_staff,
            country_programme=self.country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            date_sent_to_partner=timezone.now().date(),
            agreement__country_programme=self.country_programme,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            budget_owner=UserFactory(),
            partner_accepted=True,
            unicef_accepted=True,
        )
        ReportingRequirementFactory(intervention=self.review_intervention)
        self.review = InterventionReviewFactory(
            intervention=self.review_intervention,
            review_date=timezone.now().date(),
            meeting_date=timezone.now().date(),
            submitted_by=UserFactory(),
            review_type='prc',
            overall_approver=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.review_intervention.unicef_focal_points.add(UserFactory())
        self.review_intervention.sections.add(SectionFactory())
        self.review_intervention.offices.add(OfficeFactory())
        self.review_intervention.partner_focal_points.add(self.partner_focal_point_staff)


class TestPermissionsMixin:
    def get_permissions(self, intervention, user):
        response = self.forced_auth_req('get', reverse('pmp_v3:intervention-detail', args=[intervention.pk]), user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['permissions']


class OverallReviewTestCase(ReviewInterventionMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.prc_secretary = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PRC_SECRETARY])
        self.url = reverse('pmp_v3:intervention-reviews-detail', args=[self.review_intervention.pk, self.review.pk])

    def test_details(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-reviews-detail', args=[self.review_intervention.pk, self.review.pk]),
            self.prc_secretary
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('submitted_by', response.data)

    def test_officers_update(self):
        first_officer = UserFactory()
        second_officer = UserFactory()
        third_officer = UserFactory()
        self.review.prc_officers.add(first_officer, second_officer)
        response = self.forced_auth_req(
            'patch', self.url, self.prc_secretary,
            data={'prc_officers': [first_officer.id, third_officer.id]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(sorted(response.data['prc_officers'])),
            [first_officer.id, third_officer.id],
        )
        self.assertEqual(
            list(sorted(self.review.prc_officers.values_list('id', flat=True))),
            [first_officer.id, third_officer.id],
        )

    def test_review_update_other_user(self):
        response = self.forced_auth_req(
            'patch', self.url, UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
            data={'prc_officers': []},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('etools.applications.partners.models.send_notification_with_template')
    def test_send_notification(self, notify_mock):
        self.review.prc_officers.add(UserFactory())

        def _notify_users():
            response = self.forced_auth_req(
                'post',
                reverse('pmp_v3:intervention-reviews-notify', args=[self.review_intervention.pk, self.review.pk]),
                self.prc_secretary
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        _notify_users()
        notify_mock.assert_called()

        notify_mock.reset_mock()
        _notify_users()
        notify_mock.assert_not_called()

        self.review.prc_officers.add(UserFactory())
        _notify_users()
        notify_mock.assert_called()


class PRCReviewTestCase(ReviewInterventionMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.list_url = reverse(
            'pmp_v3:intervention-officers-review-list',
            args=[self.review_intervention.pk, self.review.pk],
        )

    def get_detail_url(self, prc_member):
        return reverse(
            'pmp_v3:intervention-officers-review-detail',
            args=[self.review_intervention.pk, self.review.pk, prc_member.pk]
        )

    def test_prc_review_created(self):
        prc_member = UserFactory()
        self.assertEqual(self.review.prc_reviews.count(), 0)
        self.review.prc_officers.add(prc_member)
        self.assertEqual(self.review.prc_reviews.count(), 1)
        self.assertEqual(self.review.prc_reviews.first().user, prc_member)

    def test_prc_review_list(self):
        prc_member = UserFactory()
        self.review.prc_officers.add(prc_member)
        user = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])
        response = self.forced_auth_req('get', self.list_url, user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(
            sorted([obj['id'] for obj in response.data]),
            [self.review.prc_reviews.get(user=prc_member).id],
        )

    def test_list_non_staff_forbidden(self):
        response = self.forced_auth_req('get', self.list_url, UserFactory())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit(self):
        prc_member = UserFactory(is_staff=True)
        self.review.prc_officers.add(prc_member)
        prc_review = self.review.prc_reviews.get()
        response = self.forced_auth_req(
            'patch', self.get_detail_url(prc_member), prc_member,
            data={'overall_comment': 'ok'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        prc_review.refresh_from_db()
        self.assertEqual(prc_review.overall_comment, 'ok')

    def test_edit_by_another_prc_officer_forbidden(self):
        prc_member = UserFactory(is_staff=True)
        another_prc_member = UserFactory(is_staff=True)
        self.review.prc_officers.add(prc_member, another_prc_member)
        response = self.forced_auth_req(
            'patch', self.get_detail_url(prc_member), another_prc_member,
            data={'overall_comment': 'ok'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_review_action_available(self):
        prc_member = UserFactory(is_staff=True)
        self.review.prc_officers.add(prc_member)
        response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[self.review_intervention.pk]), prc_member,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn('individual_review', response.data['available_actions'])

    def test_review_action_not_available_after_submit(self):
        prc_member = UserFactory(is_staff=True)
        self.review.prc_officers.add(prc_member)
        self.review.prc_reviews.filter(user=prc_member).update(overall_approval=True)
        response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[self.review_intervention.pk]), prc_member,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('individual_review', response.data['available_actions'])

    def test_create_intervention_snapshot(self):
        prc_member = UserFactory(is_staff=True)
        self.review.prc_officers.add(prc_member)
        prc_review = self.review.prc_reviews.get()
        response = self.forced_auth_req(
            'patch', self.get_detail_url(prc_member), prc_member,
            data={'overall_comment': 'ok'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        activity = Activity.objects.first()
        self.assertEqual(activity.target, self.review_intervention)
        self.assertEqual(
            'ok',
            activity.change['reviews'][0]['prc_reviews'][0]['overall_comment']['after'],
        )
        self.assertIn(
            prc_review.id,
            [pr['pk'] for pr in itertools.chain(*[r['prc_reviews'] for r in activity.data['reviews']])],
        )


class DevelopPermissionsTestCase(TestPermissionsMixin, DevelopInterventionMixin, BaseTenantTestCase):
    def test_unicef_user_permissions(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        permissions = self.get_permissions(self.develop_intervention, user)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertFalse(permissions['view']['prc_reviews'])

    def test_partner_user_permissions(self):
        response = self.forced_auth_req(
            'get', reverse('pmp_v3:intervention-detail', args=[self.develop_intervention.pk]),
            self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_secretary_permissions(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PRC_SECRETARY])
        permissions = self.get_permissions(self.develop_intervention, user)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertFalse(permissions['view']['prc_reviews'])


class DevelopSentToPartnerPermissionsTestCase(TestPermissionsMixin, DevelopInterventionMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.develop_intervention.date_sent_to_partner = timezone.now().date()
        self.develop_intervention.save()

    def test_partner_user_permissions(self):
        permissions = self.get_permissions(self.develop_intervention, self.partner_focal_point)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertFalse(permissions['view']['reviews'])
        self.assertFalse(permissions['view']['prc_reviews'])


class ReviewPermissionsTestCase(TestPermissionsMixin, ReviewInterventionMixin, BaseTenantTestCase):
    def test_unicef_user_permissions(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        permissions = self.get_permissions(self.review_intervention, user)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertTrue(permissions['view']['prc_reviews'])

    def test_partner_user_permissions(self):
        permissions = self.get_permissions(self.review_intervention, self.partner_focal_point)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertFalse(permissions['view']['reviews'])
        self.assertFalse(permissions['view']['prc_reviews'])

    def test_secretary_permissions(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PRC_SECRETARY])
        permissions = self.get_permissions(self.review_intervention, user)
        self.assertTrue(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertTrue(permissions['view']['prc_reviews'])

    def test_overall_approver_permissions(self):
        permissions = self.get_permissions(self.review_intervention, self.review.overall_approver)
        self.assertTrue(permissions['edit']['reviews'])
        self.assertFalse(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertTrue(permissions['view']['prc_reviews'])

    def test_prc_reviewer_permissions(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        self.review.prc_officers.add(user)
        permissions = self.get_permissions(self.review_intervention, user)
        self.assertFalse(permissions['edit']['reviews'])
        self.assertTrue(permissions['edit']['prc_reviews'])
        self.assertTrue(permissions['view']['reviews'])
        self.assertTrue(permissions['view']['prc_reviews'])
