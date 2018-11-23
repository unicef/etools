from django.db import models

from unicef_attachments.models import Attachment


class FieldMonitoringGeneralAttachmentManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(code='fm_common')


class FieldMonitoringGeneralAttachment(Attachment):
    """
    Proxy model for correct defining of permissions
    """

    objects = FieldMonitoringGeneralAttachmentManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        self.code = 'fm_common'
        super().save(*args, **kwargs)
