from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices


class LogIssue(models.Model):
    STATUS_CHOICES = Choices(
        ('new', 'New'),
        ('past', 'Past'),
    )

    content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        verbose_name=_('Content Type'),
        related_name="log_issues",
        on_delete=models.CASCADE,
    )
    object_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Object ID')
    )
    related_to = GenericForeignKey()
    issue = models.TextField(verbose_name=_('Issue For Attention/Probing'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CHOICES.new)
    attachments = GenericRelation('attachments.Attachment', verbose_name=_('Attachments'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    def __str__(self):
        return '{}: {}'.format(self.related_to, self.issue)
