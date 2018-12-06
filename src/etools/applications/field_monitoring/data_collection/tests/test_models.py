from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import StartedMethodFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.visits.tests.factories import UNICEFVisitFactory, TaskCheckListItemFactory, \
    VisitMethodTypeFactory, VisitCPOutputConfigFactory


class StartedMethodTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_create(self):
        visit = UNICEFVisitFactory(tasks__count=2)
        method_type = VisitMethodTypeFactory()
        TaskCheckListItemFactory(visit_task=visit.visit_task_links.first(), methods=[method_type.method])
        VisitCPOutputConfigFactory(visit_task=visit.visit_task_links.first(), recommended_method_types=[method_type])

        started_method = StartedMethodFactory(visit=visit, method=method_type.method, method_type=method_type)

        self.assertEqual(started_method.tasks_data.count(), 1)
        self.assertEqual(started_method.tasks_data.first().is_probed, None)
