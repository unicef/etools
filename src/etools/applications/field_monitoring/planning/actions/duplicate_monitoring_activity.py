from django.db import transaction

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import MonitoringActivity


class MonitoringActivityNotFound(Exception):
    pass


class DuplicateMonitoringActivity:
    @transaction.atomic
    def execute(self, monitoring_activity_id: int, with_checklist: bool, user) -> MonitoringActivity:
        try:
            activity = (MonitoringActivity.objects.select_related('location', 'location_site')
                        .prefetch_related('partners','interventions', 'cp_outputs', 'offices',
                                          'sections', 'team_members', 'questions')
                        .get(id=monitoring_activity_id))
        except MonitoringActivity.DoesNotExist:
            raise MonitoringActivityNotFound

        duplicated_activity = MonitoringActivity.objects.create(
            status=MonitoringActivity.STATUS_DRAFT,
            monitor_type=activity.monitor_type,
            location_site=activity.location_site,
            location=activity.location,
        )
        self._add_many_to_many_relations(activity, duplicated_activity)

        if with_checklist:
            self._duplicate_checklist(activity, duplicated_activity)
            duplicated_activity.status = MonitoringActivity.STATUS_CHECKLIST

        duplicated_activity.save()

        validator = ActivityValid(duplicated_activity, user=user)
        # if not validator.is_valid:
        #     logging.debug(validator.errors)
        #     raise ValidationError(validator.errors)

        return duplicated_activity

    def _add_many_to_many_relations(self, activity, duplicated_activity):
        duplicated_activity.partners.set(activity.partners.all())
        duplicated_activity.interventions.set(activity.interventions.all())
        duplicated_activity.cp_outputs.set(activity.cp_outputs.all())
        duplicated_activity.offices.set(activity.offices.all())
        duplicated_activity.sections.set(activity.sections.all())
        duplicated_activity.team_members.set(activity.team_members.all())

    def _duplicate_checklist(self, activity, duplicated_activity):
        duplicated_questions = []
        for question in activity.questions.all():
            duplicated_question = question.duplicate()
            duplicated_question.monitoring_activity = duplicated_activity
            duplicated_questions.append(duplicated_question)

        ActivityQuestion.objects.bulk_create(duplicated_questions)
