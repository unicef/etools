from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.offline.synchronizer import (
    MonitoringActivityOfflineSynchronizer,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.planning.models import (
    MonitoringActivity,
    MonitoringActivityActionPoint,
    QuestionTemplate,
)


@receiver(post_save, sender=Question)
def create_base_question_template(instance, created, **kwargs):
    if created:
        QuestionTemplate.objects.create(question=instance)


@receiver(m2m_changed, sender=MonitoringActivity.team_members.through)
def update_blueprints_visibility_on_team_members_change(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if instance.status == MonitoringActivity.STATUSES.data_collection \
            and action in ['post_add', 'post_remove']:
        MonitoringActivityOfflineSynchronizer(instance).update_data_collectors_list()


@receiver(post_save, sender=MonitoringActivity)
def update_blueprints_visibility_on_visit_lead_changed(instance, created, **kwargs):
    if instance.status == MonitoringActivity.STATUSES.data_collection \
            and instance.visit_lead_tracker.changed():
        MonitoringActivityOfflineSynchronizer(instance).update_data_collectors_list()


@receiver(post_save, sender=MonitoringActivityActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.send_email(instance.assigned_to, 'fm/action_point_assigned', cc=[instance.assigned_by.email])


@receiver(post_save, sender=ActivityQuestionOverallFinding)
def update_is_programatic_visit_on_hact_finding_save(sender, instance, **kwargs):
    activity = instance.activity_question.monitoring_activity
    if activity.status == MonitoringActivity.STATUS_COMPLETED:
        activity.update_is_programatic_visit()


@receiver(post_save, sender=ActivityOverallFinding)
def update_is_programatic_visit_on_summary_finding_save(sender, instance, **kwargs):
    if instance.monitoring_activity.status == MonitoringActivity.STATUS_COMPLETED:
        instance.monitoring_activity.update_is_programatic_visit()
