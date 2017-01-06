from __future__ import absolute_import

import datetime
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models, connection, transaction
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from model_utils import Choices
from post_office.models import EmailTemplate

from EquiTrack.utils import send_mail


class Notification(models.Model):
    """
    Represents a notification instance from sender to recipients

    Relates to :model:`django.contrib.auth.models.User`
    """

    TYPE_CHOICES = Choices(
        ('Email', 'Email'),
    )

    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    sender = GenericForeignKey('content_type', 'object_id')
    recipients = models.ForeignKey(User, related_name="notifications")
    template_name = models.CharField(max_length=255)
    template_data = JSONField()

    def __unicode__(self):
        return "{} Notification from {}: {}".format(self.type, self.sender, self.template_data)

    @classmethod
    def create_email_template(cls, type, template_name, subject, content, html_content):
        EmailTemplate.object.create(
            name=template_name, subject=subject,
            content=content, html_content=html_content,
        )

    def send_notification(self):
        if self.type == 'Email':
            if isinstance(self.sender, User):
                sender = self.sender
            else:
                sender = settings.DEFAULT_FROM_EMAIL

            send_mail(sender, self.template_name, self.template_data, list(
                self.recipients.filter(email__isnull=False).value_list('email', flat=True)))
        else:
            pass
