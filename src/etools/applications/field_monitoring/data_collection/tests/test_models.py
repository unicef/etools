from rest_framework.exceptions import ValidationError

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.base import AssignedVisitMixin
from etools.applications.field_monitoring.data_collection.tests.factories import StartedMethodFactory, \
    CheckListItemValueFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin


class StartedMethodTestCase(FMBaseTestCaseMixin, AssignedVisitMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUpTestData()

        self.started_method = StartedMethodFactory(
            visit=self.assigned_visit,
            method=self.assigned_visit_method_type.method,
            method_type=self.assigned_visit_method_type
        )
        self.task_data = self.started_method.tasks_data.first()

    def test_create(self):
        self.assertEqual(self.started_method.tasks_data.count(), 1)
        self.assertEqual(self.started_method.tasks_data.first().is_probed, True)

    def test_complete_unfilled(self):
        with self.assertRaises(ValidationError):
            self.started_method.complete()

    def test_complete_not_probed(self):
        self.started_method.tasks_data.update(is_probed=False)
        self.started_method.complete()

    def test_complete_filled(self):
        CheckListItemValueFactory(
            task_data=self.task_data,
            checklist_item=self.assigned_visit.visit_task_links.first().checklist_items.first()
        )
        self.started_method.complete()
