from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.planning.models import QuestionTemplate


@receiver(post_save, sender=Question)
def create_base_question_template(instance, created, **kwargs):
    if created:
        QuestionTemplate.objects.create(question=instance)
