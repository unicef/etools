from rest_framework import status
from rest_framework.fields import DateTimeField

from EquiTrack.factories import UserFactory, CommentFactory, WorkplanFactory, \
    ResultWorkplanPropertyFactory, WorkplanProjectFactory
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

    def test_view_comments_list(self):
        response = self.forced_auth_req('get', '/api/comments/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

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