from django.urls import reverse
from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.users.tests.factories import UserFactory


class PRCReviewTestCase(BaseTenantTestCase):
    # user click button, info saved to intervention review (review type, etc)
    # secretary fill officers
    # secretary send notifications btn
    #   no new notification if already sent today (user added)
    # secretary fill officers
    # prc officers reject PRC
    # prc officers approve PRC
    # prc officers fill review
    # prc officers submit review
    # secretary/overall approver fill final review
    # secretary/overall approver action recommend for signature
    # secretary/overall approver action reject PRC

    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory()
        self.review = self.intervention.reviews.first()
        self.list_url = reverse('pmp_v3:intervention-officers-review-list', args=[self.intervention.pk, self.review.pk])

    def get_detail_url(self, prc_member):
        return reverse(
            'pmp_v3:intervention-officers-review-detail',
            args=[self.intervention.pk, self.review.pk, prc_member.pk]
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
        prc_review = self.review.prc_reviews.get(user=prc_member)
        response = self.forced_auth_req(
            'patch', self.get_detail_url(prc_member), another_prc_member,
            data={'overall_comment': 'ok'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
