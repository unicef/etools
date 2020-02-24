from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from etools.applications.field_monitoring.data_collection.offline.synchronizer import (
    MonitoringActivityOfflineSynchronizer,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate


@receiver(post_save, sender=Question)
def create_base_question_template(instance, created, **kwargs):
    if created:
        QuestionTemplate.objects.create(question=instance)


@receiver(m2m_changed, sender=MonitoringActivity.team_members.through)
def update_blueprints_visibility_on_team_members_change(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if instance.status == MonitoringActivity.STATUSES.data_collection \
            and action in ['post_add', 'post_delete']:
        MonitoringActivityOfflineSynchronizer(instance).update_data_collectors_list()


@receiver(post_save, sender=MonitoringActivity)
def update_blueprints_visibility_on_person_responsible_changed(instance, created, **kwargs):
    if instance.status == MonitoringActivity.STATUSES.data_collection \
            and instance.person_responsible_tracker.changed():
        MonitoringActivityOfflineSynchronizer(instance).update_data_collectors_list()
