from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import FieldDoesNotExist
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
        related_name='activity_old',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name=_('Content Type')
    )
    target_object_id = models.CharField(max_length=255, db_index=True, verbose_name=_('Target Object ID'))
    target = GenericForeignKey('target_content_type', 'target_object_id')
    action = models.CharField(
        verbose_name=_("Action"),
        max_length=50,
        choices=ACTION_CHOICES,
    )
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='by_user_old',
        verbose_name=_("By User"),
        on_delete=models.CASCADE,
    )
    data = JSONField(verbose_name=_("Data"))
    change = JSONField(verbose_name=_("Change"), blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = _("Activities")

    def __str__(self):
        return "{} {} {}".format(self.by_user, self.action, self.target)

    def by_user_display(self):
        by_user = str(self.by_user)
        if not by_user.strip():
            by_user = self.by_user.email
        return by_user

    def get_action_display(self):
        if self.action == Activity.CREATE:
            return _('Created')
        elif self.action == Activity.UPDATE:
            titles = []
            for field in self.change.keys():
                try:
                    titles.append(str(self.target._meta.get_field(field).verbose_name))
                except FieldDoesNotExist:
                    continue

            return _('Changed {}').format(', '.join(titles))
        else:
            raise NotImplementedError
