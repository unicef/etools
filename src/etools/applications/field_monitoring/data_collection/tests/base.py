from etools.applications.field_monitoring.fm_settings.tests.factories import FMMethodTypeFactory, \
    PlannedCheckListItemFactory, FMMethodFactory
from etools.applications.field_monitoring.visits.models import Visit
from etools.applications.field_monitoring.visits.tests.factories import VisitFactory


class AssignedVisitMixin(object):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.assigned_visit = VisitFactory(status=Visit.STATUS_CHOICES.draft, tasks__count=1)

        cls.assigned_method_type = FMMethodTypeFactory()
        task = cls.assigned_visit.tasks.first()

        task.cp_output_config.recommended_method_types.add(cls.assigned_method_type)
        PlannedCheckListItemFactory(
            cp_output_config=task.cp_output_config,
            methods=[cls.assigned_method_type.method, FMMethodFactory(is_types_applicable=False)]
        )

        cls.assigned_visit.assign()
        cls.assigned_visit.save()

        cls.assigned_visit_method_type = task.visit_task_links.first().cp_output_configs.first()\
            .recommended_method_types.first()
