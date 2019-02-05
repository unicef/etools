from django.utils.translation import ugettext_lazy as _

from etools.applications.audit.transitions.conditions import BaseTransitionCheck
from etools.applications.field_monitoring.visits.models import TaskCheckListItem


class StartedMethodCompletedTasksCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = super().get_errors(instance, *args, **kwargs)

        base_checklist = TaskCheckListItem.objects.filter(
            visit_task__visit=instance.visit,
            methods=instance.method
        )
        if instance.method_type:
            base_checklist = base_checklist.filter(
                visit_task__cp_output_configs__recommended_method_types=instance.method_type
            )

        for task_data in instance.tasks_data.all():
            if task_data.is_probed is None:
                errors['task_data'] = errors.get('task_data', {})
                errors['task_data'][task_data.id] = _('Please answer all questions')
                continue
            elif not task_data.is_probed:
                continue

            task_checklist = base_checklist.filter(visit_task__tasks_data=task_data)

            if task_data.checklist_values.count() != task_checklist.count():
                errors['task_data'] = errors.get('task_data', {})
                errors['task_data'][task_data.id] = _('Please answer all questions')

        return errors
