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

from notification.email import send_mail


class Notification(models.Model):
    """
    Represents a notification instance from sender to recipients

    Relates to :model:`django.contrib.auth.models.User`
    """

    TYPE_CHOICES = Choices(
        ('Email', 'Email'),
    )

    TEMPLATE_NAME_CHOICES = Choices(
        ('trips/trip/created/updated', 'trips/trip/created/updated')
        ('trips/trip/approved', 'trips/trip/approved')
        ('trips/trip/approved', 'trips/trip/approved')
        ('trips/trip/cancelled', 'trips/trip/cancelled')
        ('trips/trip/completed', 'trips/trip/completed')
        ('trips/trip/representative', 'trips/trip/representative')
        ('travel/trip/travel_or_admin_assistant', 'travel/trip/travel_or_admin_assistant')
        ('trips/trip/TA_request', 'trips/trip/TA_request')
        ('trips/trip/TA_drafted', 'trips/trip/TA_drafted')
        ('trips/action/created/updated/closed', 'trips/action/created/updated/closed')
        ('trips/trip/summary', 'trips/trip/summary')
        ('partners/partnership/created/updated', 'partners/partnership/created/updated')
    )

    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    sender = GenericForeignKey('content_type', 'object_id')
    recipients = ArrayField(
        models.CharField(max_length=255),
    )
    sent_recipients = ArrayField(
        models.CharField(max_length=255),
    )
    template_name = models.CharField(max_length=255, choices=TEMPLATE_NAME_CHOICES)
    template_data = JSONField()

    def __unicode__(self):
        return "{} Notification from {}: {}".format(self.type, self.sender, self.template_data)

    def send_notification(self):
        if self.type == 'Email':
            if isinstance(self.sender, User):
                sender = self.sender
            else:
                sender = settings.DEFAULT_FROM_EMAIL

            send_mail(sender, recipients, self.template_name, self.template_data)

        else:
            pass
