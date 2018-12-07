from django.db import models
from django_fsm import FSMField, transition
from model_utils import Choices


class SimplifiedTestParent(models.Model):
    test_field = models.CharField(max_length=10)


class SimplifiedTestChild(models.Model):
    parent = models.ForeignKey(SimplifiedTestParent, related_name='children', on_delete=models.CASCADE)
    test_field = models.CharField(max_length=10)


class SimplifiedTestModelWithFSMField(models.Model):
    STATUSES = Choices(
        ('draft', 'Draft'),
        ('started', 'Active'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled'),
    )

    status = FSMField(max_length=30, choices=STATUSES, default=STATUSES.draft, protected=True)

    @transition(status, source=STATUSES.draft, target=STATUSES.started)
    def start(self):
        pass

    @transition(status, source=STATUSES.started, target=STATUSES.finished)
    def finish(self):
        pass

    @transition(status, source=[STATUSES.draft, STATUSES.started, STATUSES.finished], target=STATUSES.cancelled)
    def cancel(self):
        pass
