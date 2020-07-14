from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel


class Comment(TimeStampedModel, models.Model):
    STATES = Choices(
        ('active', _('Active')),
        ('resolved', _('resolved')),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             on_delete=models.PROTECT, related_name='comments')
    state = models.CharField(verbose_name=_('State'), max_length=10, choices=STATES, default=STATES.active)
    instance_related_ct = models.ForeignKey(ContentType, verbose_name=_('Content Type'), on_delete=models.CASCADE)
    instance_related_id = models.IntegerField(verbose_name=_('Object ID'))
    instance_related = GenericForeignKey(ct_field='instance_related_ct', fk_field='instance_related_id')
    users_related = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='mentions')
    related_to_description = models.TextField(blank=True)
    related_to = models.CharField(max_length=100)
    text = models.TextField()

    class Meta:
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        ordering = ('created',)

    def __str__(self):
        return f'{self.user}: {self.text}'
