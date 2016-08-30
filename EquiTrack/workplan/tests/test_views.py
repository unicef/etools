from rest_framework import status

from EquiTrack.factories import TripFactory, UserFactory, CommentFactory
from EquiTrack.tests.mixins import APITenantTestCase



class TestWorkplanViews(APITenantTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.comment = CommentFactory(author=self.user)

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)