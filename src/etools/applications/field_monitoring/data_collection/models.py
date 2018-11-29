from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_fsm import transition, FSMField
from model_utils import Choices

from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.field_monitoring.visits.models import Visit, VisitMethodType


class StartedMethod(models.Model):
    STATUS_CHOICES = Choices(
        ('started', _('Started')),
        ('completed', _('Completed')),
    )

    visit = models.ForeignKey(Visit, related_name='started_methods', verbose_name=_('Visit'))
    method = models.ForeignKey(FMMethod, related_name='started_methods', verbose_name=_('Method'))
    method_type = models.ForeignKey(VisitMethodType, related_name='started_methods', verbose_name=_('Method Type'),
                                    blank=True, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='started_methods', verbose_name=_('Author'))
    status = FSMField(choices=STATUS_CHOICES, default=STATUS_CHOICES.started)

    @transition(
        status, source=STATUS_CHOICES.started, target=STATUS_CHOICES.completed,
    )
    def complete(self):
        pass
