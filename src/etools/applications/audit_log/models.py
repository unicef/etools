from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from model_utils.models import TimeStampedModel

from etools.applications.audit_log.constants import GROUP_TO_AUDIT_APP_LABELS


def get_allowed_app_labels(user):
    user_group_names = set(user.groups.values_list('name', flat=True))
    allowed = set()
    for group_name in user_group_names:
        allowed.update(GROUP_TO_AUDIT_APP_LABELS.get(group_name, []))
    return allowed


class AuditLogQuerySet(models.QuerySet):

    def for_user(self, user):
        if user.is_superuser:
            return self
        allowed = get_allowed_app_labels(user)
        if not allowed:
            return self.none()
        return self.filter(content_type__app_label__in=allowed)


class AuditLogEntry(TimeStampedModel, models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_SOFT_DELETE = 'SOFT_DELETE'

    ACTION_CHOICES = (
        (ACTION_CREATE, _('Created')),
        (ACTION_UPDATE, _('Updated')),
        (ACTION_DELETE, _('Deleted')),
        (ACTION_SOFT_DELETE, _('Soft Deleted')),
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
    )
    object_id = models.CharField(
        max_length=255,
        verbose_name=_("Object ID"),
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_("Action"),
    )
    changed_fields = models.JSONField(
        verbose_name=_("Changed Fields"),
        null=True,
        blank=True,
        help_text=_("List of field names that were changed"),
    )
    old_values = models.JSONField(
        verbose_name=_("Previous Values"),
        null=True,
        blank=True,
    )
    new_values = models.JSONField(
        verbose_name=_("New Values"),
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_log_entries',
        verbose_name=_("User"),
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description"),
        help_text=_("Optional human-readable description of the change"),
    )

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ['-created']
        verbose_name = _('Audit Log Entry')
        verbose_name_plural = _('Audit Log Entries')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['content_type', 'object_id', '-created']),
            models.Index(fields=['action']),
            models.Index(fields=['user']),
            models.Index(fields=['created']),
        ]

    def __str__(self):
        return (
            f'{self.content_type.model} #{self.object_id} - '
            f'{self.get_action_display()} at {self.created}'
        )
