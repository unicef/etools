from django.contrib.auth.models import AnonymousUser

from rest_framework import status

from etools.applications.comments.models import Comment
from etools.applications.comments.tests.factories import CommentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestCommentsViewSet(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'comments:comments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_user = UserFactory()
        cls.example_intervention = InterventionFactory()

    def get_list_args(self):
        return ['partners', 'intervention', self.example_intervention.id]

    def test_list(self):
        CommentFactory(instance_related=PartnerFactory())
        valid_comments = CommentFactory.create_batch(5, instance_related=self.example_intervention)

        self._test_list(self.unicef_user, valid_comments)

    def test_anonymous(self):
        self._test_list(AnonymousUser(), [], expected_status=status.HTTP_403_FORBIDDEN)

    def test_create_minimal(self):
        self._test_create(self.unicef_user, {'related_to': 'root', 'text': 'test'})

    def test_create(self):
        response = self._test_create(
            self.unicef_user,
            {'related_to': 'root', 'text': 'test', 'users_related': [self.unicef_user.id]}
        )
        comment = Comment.objects.get(id=response.data['id'])
        self.assertEqual(comment.user, self.unicef_user)
        self.assertListEqual(list(comment.users_related.values_list('id', flat=True)), [self.unicef_user.id])
        self.assertEqual(comment.instance_related, self.example_intervention)

    def test_update(self):
        comment = CommentFactory(
            user=self.unicef_user, instance_related=self.example_intervention,
            users_related=[self.unicef_user]
        )
        self.assertEqual(list(comment.users_related.values_list('id', flat=True)), [self.unicef_user.id])
        second_user = UserFactory()

        self._test_update(
            self.unicef_user, comment,
            {'users_related': [second_user.id], 'text': 'new_text'}
        )

        comment.refresh_from_db()
        self.assertEqual(list(comment.users_related.values_list('id', flat=True)), [second_user.id])
        self.assertEqual(comment.text, 'new_text')

    def test_update_not_owned_comment(self):
        self._test_update(
            self.unicef_user, CommentFactory(instance_related=self.example_intervention), {},
            expected_status=status.HTTP_403_FORBIDDEN
        )

    def test_resolve(self):
        comment = CommentFactory(user=self.unicef_user, instance_related=self.example_intervention)

        response = self.make_request_to_viewset(self.unicef_user, method='post', data={},
                                                instance=comment, action='resolve')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        comment.refresh_from_db()
        self.assertEqual(comment.state, Comment.STATES.resolved)

    def test_resolve_not_owned(self):
        comment = CommentFactory(instance_related=self.example_intervention)

        response = self.make_request_to_viewset(self.unicef_user, method='post', data={},
                                                instance=comment, action='resolve')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
