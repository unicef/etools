from django.db import models
from django_fsm import FSMField, transition
from model_utils import Choices


class Parent(models.Model):
    test_field = models.CharField(max_length=10)


class Child(models.Model):
    parent = models.ForeignKey(Parent, related_name='children')
    test_field = models.CharField(max_length=10)


class ModelWithFSMField(models.Model):
    STATUSES = Choices(
        ('draft', 'Draft'),
        ('started', 'Active'),
        ('finished', 'Finished'),
    )

    status = FSMField(max_length=30, choices=STATUSES, default=STATUSES.draft, protected=True)

    @transition(status, source=STATUSES.draft, target=STATUSES.started)
    def start(self):
        pass

    @transition(status, source=STATUSES.started, target=STATUSES.finished)
    def finish(self):
        pass
