from __future__ import unicode_literals

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel


class Activity(TimeStampedModel):
    CREATE = "create"
    UPDATE = "update"
    ACTION_CHOICES = (
        (CREATE, _("Create")),
        (UPDATE, _("Update")),
    )

    target_content_type = models.ForeignKey(
        ContentType,
        related_name='activity',
        on_delete=models.CASCADE,
        db_index=True
    )
    target_object_id = models.CharField(max_length=255, db_index=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')
    action = models.CharField(
        verbose_name=_("Action"),
        max_length=50,
        choices=ACTION_CHOICES,
    )
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("By User"),
    )
    data = JSONField(verbose_name=_("Data"))
    change = JSONField(verbose_name=_("Change"), blank=True)

    class Meta:
        ordering = ["-created"]

    def __unicode__(self):
        return u"{} {} {}".format(self.by_user, self.action, self.target)
