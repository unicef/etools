from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from locations.models import Location
from partners.models import PartnerOrganization, Intervention
from reports.models import Result
from users.models import Section, Office


class ActionPoint(TimeStampedModel, models.Model):
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

    related_module = models.CharField(max_length=20, choices=MODULE_CHOICES, blank=True, null=True)

    # todo: implement list of allowed content_types by app_labels/model_names/etc?
    related_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    related_object = GenericForeignKey(ct_field='related_content_type', fk_field='related_object_id')

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_action_points',
                               verbose_name=_('Assigned By'))
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_action_points',
                                    verbose_name=_('Assigned To'))

    status = FSMField(verbose_name=_('Status'), max_length=10, choices=STATUSES, default=STATUSES.open, protected=True)

    description = models.TextField(verbose_name=_('Description'))
    due_date = models.DateField(verbose_name=_('Due Date'), blank=True, null=True)

    action_taken = models.TextField(verbose_name=_('Action Taken'), blank=True)

    section = models.ForeignKey(Section, verbose_name=_('Section'))
    office = models.ForeignKey(Office, verbose_name=_('Office'))
    location = models.ForeignKey(Location, verbose_name=_('Location'), blank=True, null=True)
    partner = models.ForeignKey(PartnerOrganization, verbose_name=_('Partner'))
    cp_output = models.ForeignKey(Result, verbose_name=_('CP Output'))
    intervention = models.ForeignKey(Intervention, verbose_name=_('PD/SSFA'))

    date_of_complete = MonitorField(verbose_name=_('Date Action Point Completed'), null=True, blank=True,
                                    monitor='status', when=[STATUSES.completed])

    def get_related_module(self):
        if self.related_module:
            return self.related_module

        if not self.related_content_type:
            return

        return self.MODULES_MAPPING.get(self.related_content_type.app_label)

    @transition(status, source=STATUSES.open, target=STATUSES.completed)
    def complete(self):
        # todo: action_taken required
        pass
