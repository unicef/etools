import factory.fuzzy

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import CheckListItemFactory, \
    PlannedCheckListItemFactory, PlannedCheckListItemPartnerInfoFactory, FMMethodTypeFactory, CPOutputConfigFactory
from etools.applications.field_monitoring.planning.tests.factories import TaskFactory
from etools.applications.field_monitoring.visits.models import TaskCheckListItem, VisitMethodType
from etools.applications.field_monitoring.visits.tests.factories import VisitFactory


class TestTaskCheckListItem(BaseTenantTestCase):
    def test_generate_for_visit(self):
        first_item = CheckListItemFactory()
        second_item = CheckListItemFactory()
        CheckListItemFactory()  # should be unused

        task = TaskFactory()

        planned_first_item = PlannedCheckListItemFactory(
            cp_output_config=task.cp_output_config,
            checklist_item=first_item, methods__count=2
        )
        planned_second_item = PlannedCheckListItemFactory(
            cp_output_config=task.cp_output_config,
            checklist_item=second_item, methods__count=3
        )

        first_item_partner_info = PlannedCheckListItemPartnerInfoFactory(
            planned_checklist_item=planned_first_item,
            partner=task.partner,
            specific_details=factory.fuzzy.FuzzyText()
        )
        second_item_partner_info = PlannedCheckListItemPartnerInfoFactory(
            planned_checklist_item=planned_second_item,
            partner=None,
            specific_details=factory.fuzzy.FuzzyText()
        )

        visit = VisitFactory(tasks=[task])

        with self.assertNumQueries(9 + 4*2):  # two visit checklist items should be created
            TaskCheckListItem.generate_for_visit(visit)

        visit_task_checklist = TaskCheckListItem.objects.filter(visit_task__visit=visit, visit_task__task=task)\
            .order_by('id')

        self.assertEqual(visit_task_checklist.count(), 2)
        self.assertEqual(visit_task_checklist[0].specific_details, first_item_partner_info.specific_details)
        self.assertEqual(visit_task_checklist[1].specific_details, second_item_partner_info.specific_details)


class TestVisitMethodType(BaseTenantTestCase):
    def test_generate_for_visit(self):
        first_method_type = FMMethodTypeFactory()
        second_method_type = FMMethodTypeFactory()
        third_method_type = FMMethodTypeFactory()

        task = TaskFactory()
        visit = VisitFactory(tasks=[task])

        config = task.cp_output_config
        config.recommended_method_types.add(first_method_type, second_method_type)
        unused_config = CPOutputConfigFactory()
        unused_config.recommended_method_types.add(third_method_type)

        VisitMethodType.generate_for_visit(visit)

        visit_method_types = VisitMethodType.objects.filter(visit=visit)

        self.assertEqual(visit_method_types.count(), 2)
        self.assertEqual(
            list(visit_method_types.values_list('name', flat=True).order_by('id')),
            [first_method_type.name, second_method_type.name]
        )
