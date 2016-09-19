from django.core import mail
from rest_framework import status
from rest_framework.fields import DateTimeField

from EquiTrack.factories import UserFactory, CommentFactory, WorkplanFactory, \
    ResultWorkplanPropertyFactory, WorkplanProjectFactory, LabelFactory
from EquiTrack.tests.mixins import APITenantTestCase

class TestWorkplanViews(APITenantTestCase):
    maxDiff = None
    def setUp(self):
        self.user = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.workplan = WorkplanFactory()
        self.comment = CommentFactory(author=self.user, workplan=self.workplan)
        self.resultworkplanproperty = ResultWorkplanPropertyFactory(workplan=self.workplan)
        self.workplan_project = WorkplanProjectFactory(workplan=self.workplan)
        self.labels = [LabelFactory() for x in xrange(3)]
        self.resultworkplanproperty = ResultWorkplanPropertyFactory(
                                            workplan=self.workplan,
                                            labels=self.labels
                                        )
        self.extra_label = LabelFactory()
        self.user2 = UserFactory()

        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('post', '/api/comments/', data=data)
        self.comment2 = response.data

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_view_workplans_list(self):
        response = self.forced_auth_req('get', '/api/workplans/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]

        comment_timestamp = DateTimeField().to_representation(self.comment.timestamp)
        self.assertEqual(payload,
                         {'id': self.workplan.id,
                          'status': None,
                          'result_structure': self.workplan.result_structure.id,
                          'comments': [{'id': self.comment.id,
                                        'author': self.comment.author.id,
                                        'tagged_users': [],
                                        'text': self.comment.text,
                                        'timestamp': comment_timestamp}],
                          'workplan_projects': [self.workplan_project.id]})

    def test_view_resultworkplanproperties_list(self):
        response = self.forced_auth_req('get', '/api/resultworkplanproperties/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_view_workplanprojects_list(self):
        response = self.forced_auth_req('get', '/api/workplan_projects/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]

        cover_page = self.workplan_project.cover_page
        self.assertEqual(dict(payload),
                         {'id': self.workplan_project.id,
                          'workplan': self.workplan.id,
                          'cover_page': {'id': cover_page.id,
                                         'national_priority': cover_page.national_priority,
                                         'responsible_government_entity': cover_page.responsible_government_entity,
                                         'planning_assumptions': cover_page.planning_assumptions,
                                         'logo': None}})

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

    def test_view_comments_create(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('post', '/api/comments/', data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_view_comments_update(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_view_comments_update_email(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox[1].subject, "You are tagged on a comment")

    def test_view_comments_update_remove(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)
        data = {
            "author": self.user.id,
            "tagged_users": [self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
