from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import six
from django.utils.six import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from EquiTrack.utils import get_environment
from action_points.conditions import ActionPointCompleteRequiredFieldsCheck
from locations.models import Location
from notification.models import Notification
from partners.models import PartnerOrganization, Intervention
from reports.models import Result
from users.models import Section, Office


@python_2_unicode_compatible
class ActionPoint(TimeStampedModel):
    MODULE_CHOICES = Choices(
        ('t2f', 'Trip Management'),
        ('tpm', 'Third Party Monitoring'),
        ('audit', 'Auditor Portal'),
    )

    MODULES_MAPPING = {
        't2f': MODULE_CHOICES.t2f,
        'tpm': MODULE_CHOICES.tpm,
        'audit': MODULE_CHOICES.audit,
    }

    STATUSES = Choices(
        ('open', _('Open')),
        ('completed', _('Completed')),
    )

    HIGH_PRIORITY_CHOICES = Choices(
        ('yes', _('Yes')),
        ('no', _('No')),
    )

    STATUSES_DATES = {
        STATUSES.open: 'created',
        STATUSES.completed: 'date_of_complete'
    }

    KEY_EVENTS = Choices((
        ('status_update', 'Status Update'),
        ('reassign', 'Reassign'),
    ))

    related_module = models.CharField(max_length=20, choices=MODULE_CHOICES, blank=True, null=True)

    related_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    related_object = GenericForeignKey(ct_field='related_content_type', fk_field='related_object_id')

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_action_points',
                               verbose_name=_('Author'))
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', verbose_name=_('Assigned By'))
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_action_points',
                                    verbose_name=_('Assigned To'))

    status = FSMField(verbose_name=_('Status'), max_length=10, choices=STATUSES, default=STATUSES.open, protected=True)

    description = models.TextField(verbose_name=_('Description'))
    due_date = models.DateField(verbose_name=_('Due Date'), blank=True, null=True)
    high_priority = models.CharField(choices=HIGH_PRIORITY_CHOICES, default=HIGH_PRIORITY_CHOICES.no, max_length=10,
                                     verbose_name=_('High Priority'))

    action_taken = models.TextField(verbose_name=_('Action Taken'), blank=True)

    section = models.ForeignKey(Section, verbose_name=_('Section'))
    office = models.ForeignKey(Office, verbose_name=_('Office'))
    location = models.ForeignKey(Location, verbose_name=_('Location'), blank=True, null=True)
    partner = models.ForeignKey(PartnerOrganization, verbose_name=_('Partner'))
    cp_output = models.ForeignKey(Result, verbose_name=_('CP Output'), blank=True, null=True)
    intervention = models.ForeignKey(Intervention, verbose_name=_('PD/SSFA'), blank=True, null=True)

    date_of_complete = MonitorField(verbose_name=_('Date Action Point Completed'), null=True, blank=True,
                                    monitor='status', when=[STATUSES.completed])

    comments = GenericRelation('django_comments.Comment', object_id_field='object_pk')

    history = GenericRelation('snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    tracker = FieldTracker()

    class Meta:
        ordering = ('related_module', 'related_content_type', 'related_object_id')

    def save(self, **kwargs):
        if self.related_content_type:
            related_module = self.MODULES_MAPPING.get(self.related_content_type.app_label)
            if related_module != self.related_module:
                self.related_module = related_module

        super(ActionPoint, self).save(**kwargs)

    @property
    def reference_number(self):
        return '{0}/{1}/ACTP'.format(
            self.created.year,
            self.id,
        )

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    def __str__(self):
        return self.reference_number

    def get_additional_data(self, diff):
        key_events = []
        if 'status' in diff:
            key_events.append(self.KEY_EVENTS.status_update)
        if 'assigned_to' in diff:
            key_events.append(self.KEY_EVENTS.reassign)

        return {'key_events': key_events}

    def get_mail_context(self):
        return {
            'person_responsible': self.assigned_to.get_full_name(),
            'assigned_by': self.assigned_by.get_full_name(),
            'reference_number': self.reference_number,
            'implementing_partner': six.text_type(self.partner),
            'description': self.description,
            'due_date': self.due_date.strftime('%d %b %Y'),
            'object_url': 'link to follow up',
        }

    def send_email(self, recipient, template_name):
        context = {
            'environment': get_environment(),
            'action_point': self.get_mail_context(),
            'recipient': recipient.get_full_name(),
        }

        notification = Notification.objects.create(
            sender=self,
            recipients=[recipient.email], template_name=template_name,
            template_data=context
        )
        notification.send_notification()

    @transition(status, source=STATUSES.open, target=STATUSES.completed,
                conditions=[
                    ActionPointCompleteRequiredFieldsCheck.as_condition()
                ])
    def complete(self):
        self.send_email(self.assigned_by, 'action_points/action_point/completed')
