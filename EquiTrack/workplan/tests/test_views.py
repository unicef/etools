import random

from rest_framework import status

from EquiTrack.factories import UserFactory, CommentFactory, WorkplanFactory, \
    ResultWorkplanPropertyFactory, LabelFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestWorkplanViews(APITenantTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.comment = CommentFactory(author=self.user)
        self.workplan = WorkplanFactory()
        self.labels = [LabelFactory() for x in xrange(3)]
        self.resultworkplanproperty = ResultWorkplanPropertyFactory(
                                            workplan=self.workplan,
                                            labels=self.labels
                                        )
        self.extra_label = LabelFactory()

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

    def test_view_labels_list(self):
        response = self.forced_auth_req('get', '/api/labels/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_view_labels_delete_in_use(self):
        url = '/api/labels/{}/'.format(self.labels[0].id)
        response = self.forced_auth_req('delete', url, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_labels_delete_not_in_use(self):
        url = '/api/labels/{}/'.format(self.extra_label.id)
        response = self.forced_auth_req('delete', url, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
