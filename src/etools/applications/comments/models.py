from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel


class Comment(TimeStampedModel, models.Model):
    STATES = Choices(
        ('active', _('Active')),
        ('resolved', _('Resolved')),
        ('deleted', _('Deleted')),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             on_delete=models.PROTECT, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
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

    def __str__(self) -> str:
        return f'{self.user}: {self.text}'

    def resolve(self):
        if self.state == self.STATES.deleted:
            raise ValidationError(_('Unable to resolve deleted comment'))

        self.state = self.STATES.resolved
        self.save()

    def remove(self):
        if self.replies.exists():
            raise ValidationError(_('This comment has answers. Unable to delete.'))

        self.state = self.STATES.deleted
        self.save()
