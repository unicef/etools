from django.core import mail
from rest_framework import status

from EquiTrack.factories import TripFactory, UserFactory, CommentFactory
from EquiTrack.tests.mixins import APITenantTestCase
from workplan.tasks import notify_comment_tagged_users

class TestWorkplanViews(APITenantTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user2 = UserFactory()
        self.comment = CommentFactory(author=self.user)

        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('post', '/api/comments/', data=data)
        self.comment2 = response.data

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_view_comments_create(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('post', '/api/comments/', data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_view_comments_update(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_view_comments_update_email(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)
        notify_comment_tagged_users([self.user.id, self.user2.id], self.comment2["id"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox[1].subject, "You are tagged on a comment")

    def test_view_comments_update_remove(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)
        data = {
            "author": self.user.id,
            "tagged_users": [self.user2.id],
            "text": "foobar"
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
