from rest_framework import status


from EquiTrack.factories import UserFactory, CommentFactory, WorkplanFactory, \
    ResultWorkplanPropertyFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestWorkplanViews(APITenantTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.workplan = WorkplanFactory()
        self.comment = CommentFactory(author=self.user, workplan=self.workplan)
        self.resultworkplanproperty = ResultWorkplanPropertyFactory(workplan=self.workplan)

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_view_workplans_list(self):
        response = self.forced_auth_req('get', '/api/workplans/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_view_resultworkplanproperties_list(self):
        response = self.forced_auth_req('get', '/api/resultworkplanproperties/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
