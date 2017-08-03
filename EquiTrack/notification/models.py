from __future__ import absolute_import

import json
import logging
import six

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.template.base import Template, VariableNode

from model_utils import Choices
from post_office import mail
from post_office.models import EmailTemplate


logger = logging.getLogger(__name__)


class Notification(models.Model):
    """
    Represents a notification instance from sender to recipients
    """

    TYPE_CHOICES = Choices(
        ('Email', 'Email'),
    )

    TEMPLATE_NAME_CHOICES = Choices(
        ('trips/trip/created/updated', 'trips/trip/created/updated'),
        ('trips/trip/approved', 'trips/trip/approved'),
        ('trips/trip/cancelled', 'trips/trip/cancelled'),
        ('trips/trip/completed', 'trips/trip/completed'),
        ('trips/trip/representative', 'trips/trip/representative'),
        ('travel/trip/travel_or_admin_assistant', 'travel/trip/travel_or_admin_assistant'),
        ('trips/trip/TA_request', 'trips/trip/TA_request'),
        ('trips/trip/TA_drafted', 'trips/trip/TA_drafted'),
        ('trips/action/created/updated/closed', 'trips/action/created/updated/closed'),
        ('trips/trip/summary', 'trips/trip/summary'),
        ('partners/partnership/created/updated', 'partners/partnership/created/updated'),
        ('partners/partnership/signed/frs', 'partners/partnership/signed/frs')
    )

    type = models.CharField(max_length=255, default='Email')
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True)
    sender = GenericForeignKey('content_type', 'object_id')
    recipients = ArrayField(
        models.CharField(max_length=255),
    )
    sent_recipients = ArrayField(
        models.CharField(max_length=255),
        default=list
    )
    template_name = models.CharField(max_length=255)
    template_data = JSONField()

    def __unicode__(self):
        return "{} Notification from {}: {}".format(self.type, self.sender, self.template_data)

    def send_notification(self):
        """
        Dispatch notification based on type.
        """
        if self.type == 'Email':
            self.send_mail()
        else:
            # for future notification methods
            pass

    def send_mail(self):
        if isinstance(self.sender, User):
            sender = self.sender.email
        else:
            sender = settings.DEFAULT_FROM_EMAIL

        if isinstance(self.template_data, six.string_types):
            template_data = json.loads(self.template_data)
        else:
            template_data = self.template_data

        try:
            mail.send(
                recipients=self.recipients,
                sender=sender,
                template=self.template_name,
                context=template_data,
            )
        except Exception:
            # log an exception, with traceback
            logger.exception('Failed to send mail.')
        else:
            self.sent_recipients = self.recipients
            self.save()

    @classmethod
    def get_template_html_content(cls, template_name):
        try:
            email_template = EmailTemplate.objects.get(name=template_name)

            return email_template.html_content
        except EmailTemplate.DoesNotExist:
            return ''

    @classmethod
    def get_template_context_entries(cls, template_name):
        try:
            email_template = EmailTemplate.objects.get(name=template_name)
        except EmailTemplate.DoesNotExist:
            return []
        else:
            template_obj = Template(email_template.html_content)

            return map(lambda node: str(node).split(': ')[1][:-1],
                       template_obj.nodelist.get_nodes_by_type(VariableNode))
