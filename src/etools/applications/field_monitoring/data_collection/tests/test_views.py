from django.urls import reverse
from factory import fuzzy
from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.base import AssignedVisitMixin
from etools.applications.field_monitoring.data_collection.tests.factories import StartedMethodFactory, TaskDataFactory, \
    CheckListItemValueFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.visits.models import Visit, TaskCheckListItem, FindingMixin
from etools.applications.field_monitoring.visits.tests.factories import UNICEFVisitFactory, TaskCheckListItemFactory


class VisitDataCollectionViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_details(self):
        visit = UNICEFVisitFactory(status=Visit.STATUS_CHOICES.assigned)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:visits-detail', args=[visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StartedMethodsViewTestCase(FMBaseTestCaseMixin, AssignedVisitMixin, BaseTenantTestCase):
    def test_list(self):
        StartedMethodFactory(
            visit=self.assigned_visit,
            method=self.assigned_visit_method_type.method,
            method_type=self.assigned_visit_method_type,
        )

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:started-methods-list', args=[self.assigned_visit.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def start_new_method(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_data_collection:started-methods-list', args=[self.assigned_visit.id]),
            user=self.unicef_user,
            data={
                'method': self.assigned_visit_method_type.method.id,
                'method_type': self.assigned_visit_method_type.id,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author']['id'], self.unicef_user.id)


class TaskDataViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.visit = UNICEFVisitFactory(status=Visit.STATUS_CHOICES.assigned)
        cls.started_method = StartedMethodFactory(visit=cls.visit)
        cls.task_data = TaskDataFactory(visit_task__visit=cls.visit, started_method=cls.started_method)

    def test_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:task-data-list',
                           args=[self.visit.id, self.started_method.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_update_not_probed(self):
        task_data = TaskDataFactory(visit_task__visit=self.visit, started_method=self.started_method, is_probed=True)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_data_collection:task-data-detail',
                             args=[self.visit.id, self.started_method.id, task_data.id]),
            user=self.unicef_user,
            data={
                'is_probed': False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_probed'], False)


class TaskDataCheckListViewTestCase(FMBaseTestCaseMixin, AssignedVisitMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.started_method = StartedMethodFactory(
            visit=cls.assigned_visit,
            method=cls.assigned_visit_method_type.method,
            method_type=cls.assigned_visit_method_type,
        )
        cls.task_data = cls.started_method.tasks_data.first()

    def test_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_data_collection:tasks-data-checklist-list',
                           args=[self.assigned_visit.id, self.started_method.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['checklist_values'], [])

    def test_set_value(self):
        checklist_item = TaskCheckListItem.objects.get(visit_task=self.task_data.visit_task)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_data_collection:tasks-data-checklist-detail',
                             args=[self.assigned_visit.id, self.started_method.id, checklist_item.id]),
            user=self.unicef_user,
            data={
                'checklist_values': [
                    {
                        'task_data': self.task_data.id,
                        'finding_value': fuzzy.FuzzyChoice(choices=dict(FindingMixin.FINDING_CHOICES).keys()).fuzz(),
                        'finding_description': fuzzy.FuzzyText().fuzz(),
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['checklist_values']), 1)

    def test_update_value(self):
        checklist_item = TaskCheckListItem.objects.get(visit_task=self.task_data.visit_task)
        value = CheckListItemValueFactory(checklist_item=checklist_item, task_data=self.task_data)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_data_collection:tasks-data-checklist-detail',
                             args=[self.assigned_visit.id, self.started_method.id, checklist_item.id]),
            user=self.unicef_user,
            data={
                'checklist_values': [
                    {
                        'id': value.id,
                        'finding_description': 'test',
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['checklist_values']), 1)
        self.assertEqual(response.data['checklist_values'][0]['finding_description'], 'test')
