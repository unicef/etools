from django.core import mail
from rest_framework import status

from EquiTrack.factories import UserFactory, CommentFactory, WorkplanFactory, \
    ResultWorkplanPropertyFactory, WorkplanProjectFactory, LabelFactory, ResultFactory, \
    ResultStructureFactory
from EquiTrack.tests.mixins import APITenantTestCase
from reports.models import ResultType
from workplan.tasks import notify_comment_tagged_users


class TestWorkplanViews(APITenantTestCase):
    fixtures = ['initial_data.json']

    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.workplan = WorkplanFactory()
        self.comment = CommentFactory(author=self.user, workplan=self.workplan)

        self.workplan_project = WorkplanProjectFactory(workplan=self.workplan)
        self.labels = [LabelFactory() for x in xrange(3)]
        self.result_type = ResultType.objects.get(name=ResultType.OUTPUT)
        self.result = ResultFactory(result_type=self.result_type, result_structure=ResultStructureFactory())

        self.resultworkplanproperty = ResultWorkplanPropertyFactory(
                                            workplan=self.workplan,
                                            result=self.result,
                                            labels=self.labels
                                        )
        self.extra_label = LabelFactory()
        self.user2 = UserFactory()

        self.comment2_obj = CommentFactory(author=self.user, text='foobar', workplan=self.workplan)
        data = {'tagged_users': [self.user.id]}
        response = self.forced_auth_req('patch', '/api/comments/{}/'.format(self.comment2_obj.id), data=data,
                                        user=self.unicef_staff)
        self.comment2 = response.data

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_view_workplans_list(self):
        response = self.forced_auth_req('get', '/api/workplans/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        # TODO test the following:
        # from rest_framework.fields import DateTimeField
        # payload = response.data[0]
        #
        # comment_timestamp = DateTimeField().to_representation(self.comment.modified)
        # comment2_timestamp = DateTimeField().to_representation(self.comment2_obj.modified)
        # self.assertEqual(dict(payload),
        #                  {'id': self.workplan.id,
        #                   'status': None,
        #                   'country_programme': self.workplan.country_programme.id,
        #                   'comments': [{'id': self.comment.id,
        #                                 'author': self.comment.author.id,
        #                                 'tagged_users': [],
        #                                 'text': self.comment.text,
        #                                 'modified': comment_timestamp,
        #                                 'workplan': self.workplan.id},
        #                                {'id': self.comment2_obj.id,
        #                                 'author': self.comment2_obj.author.id,
        #                                 'tagged_users': [self.user.id],
        #                                 'text': self.comment2_obj.text,
        #                                 'modified': comment2_timestamp,
        #                                 'workplan': self.workplan.id}],
        #                   'workplan_projects': [self.workplan_project.id]})

    def test_view_workplanprojects_list(self):
        response = self.forced_auth_req('get', '/api/workplan_projects/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]

        cover_page = self.workplan_project.cover_page
        payload['cover_page'] = dict(payload['cover_page'])
        self.assertEqual(dict(payload),
                         {'id': self.workplan_project.id,
                          'workplan': self.workplan.id,
                          'cover_page': {'id': cover_page.id,
                                         'national_priority': cover_page.national_priority,
                                         'responsible_government_entity': cover_page.responsible_government_entity,
                                         'planning_assumptions': cover_page.planning_assumptions,
                                         'logo': None,
                                         'budgets': [],
                                         'workplan_project': self.workplan_project.id}})

    def test_view_labels_create(self):
        data = {
            "name": "Label somethingelse"
        }
        response = self.forced_auth_req('post', '/api/labels/', data=data, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_view_labels_unique(self):
        data = {
            "name": self.labels[0].name
        }
        response = self.forced_auth_req('post', '/api/labels/', data=data, user=self.unicef_staff)

        self.assertEqual(response.data["name"][0], u'label with this name already exists.')

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
        response = self.forced_auth_req('post', '/api/comments/', data=data, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_view_comments_update(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data,
                                        user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_view_comments_update_email(self):
        data = {
            "author": self.user.id,
            "tagged_users": [self.user.id, self.user2.id],
            "text": "foobar",
            "workplan": self.workplan.id
        }
        response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data,
                                        user=self.unicef_staff)
        notify_comment_tagged_users([self.user.id, self.user2.id], self.comment2["id"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox[1].subject, "You are tagged on a comment")

    # def test_view_comments_update_remove(self):
    #     data = {
    #         "author": self.user.id,
    #         "tagged_users": [self.user.id, self.user2.id],
    #         "text": "foobar",
    #         "workplan": self.workplan.id
    #     }
    #     response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data,
    #                                     user=self.unicef_staff)
    #     data = {
    #         "author": self.user.id,
    #         "tagged_users": [self.user2.id],
    #         "text": "foobar",
    #         "workplan": self.workplan.id
    #     }
    #     response = self.forced_auth_req('put', '/api/comments/{}/'.format(self.comment2["id"]), data=data,
    #                                     user=self.unicef_staff)
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(mail.outbox), 2)
