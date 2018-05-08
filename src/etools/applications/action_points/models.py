
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import six
from django.utils.six import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from etools.applications.action_points.conditions import ActionPointCompleteRequiredFieldsCheck
from etools.applications.EquiTrack.utils import get_environment
from etools.applications.notification.models import Notification


@python_2_unicode_compatible
class ActionPoint(TimeStampedModel):
    MODULE_CHOICES = Choices(
        ('t2f', _('Trip Management')),
        ('tpm', 'Third Party Monitoring'),
        ('audit', _('Auditor Portal')),
    )

    STATUSES = Choices(
        ('open', _('Open')),
        ('completed', _('Completed')),
    )

    PRIORITY_CHOICES = Choices(
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
    )

    STATUSES_DATES = {
        STATUSES.open: 'created',
        STATUSES.completed: 'date_of_completion'
    }

    KEY_EVENTS = Choices(
        ('status_update', _('Status Update')),
        ('reassign', _('Reassign')),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_action_points',
                               verbose_name=_('Author'),
                               on_delete=models.CASCADE,
                               )
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', verbose_name=_('Assigned By'),
                                    on_delete=models.CASCADE,
                                    )
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_action_points',
                                    verbose_name=_('Assigned To'),
                                    on_delete=models.CASCADE,
                                    )

    status = FSMField(verbose_name=_('Status'), max_length=10, choices=STATUSES, default=STATUSES.open, protected=True)

    description = models.TextField(verbose_name=_('Description'))
    due_date = models.DateField(verbose_name=_('Due Date'), blank=True, null=True)
    priority = models.CharField(choices=PRIORITY_CHOICES, default=PRIORITY_CHOICES.normal, max_length=10,
                                verbose_name=_('Priority'))

    action_taken = models.TextField(verbose_name=_('Action Taken'), blank=True)

    section = models.ForeignKey('reports.Sector', verbose_name=_('Section'),
                                on_delete=models.CASCADE,
                                )
    office = models.ForeignKey('users.Office', verbose_name=_('Office'),
                               on_delete=models.CASCADE,
                               )

    location = models.ForeignKey('locations.Location', verbose_name=_('Location'), blank=True, null=True,
                                 on_delete=models.CASCADE,
                                 )
    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Partner'), blank=True, null=True,
                                on_delete=models.CASCADE,
                                )
    cp_output = models.ForeignKey('reports.Result', verbose_name=_('CP Output'), blank=True, null=True,
                                  on_delete=models.CASCADE,
                                  )
    intervention = models.ForeignKey('partners.Intervention', verbose_name=_('PD/SSFA'), blank=True, null=True,
                                     on_delete=models.CASCADE,
                                     )
    engagement = models.ForeignKey('audit.Engagement', verbose_name=_('Engagement'), blank=True, null=True,
                                   on_delete=models.CASCADE,
                                   )
    tpm_activity = models.ForeignKey('tpm.TPMActivity', verbose_name=_('TPM Activity'), blank=True, null=True,
                                     on_delete=models.CASCADE,
                                     )
    travel_activity = models.ForeignKey('t2f.TravelActivity', verbose_name=_('Travel Activity'), blank=True, null=True,
                                        on_delete=models.CASCADE,
                                        )

    date_of_completion = MonitorField(verbose_name=_('Date Action Point Completed'), null=True, blank=True,
                                      monitor='status', when=[STATUSES.completed])

    comments = GenericRelation('django_comments.Comment', object_id_field='object_pk')

    history = GenericRelation('snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    tracker = FieldTracker(fields=['assigned_to'])

    @property
    def related_module(self):
        if self.engagement:
            return self.MODULE_CHOICES.audit
        if self.tpm_activity:
            return self.MODULE_CHOICES.tpm
        if self.travel_activity:
            return self.MODULE_CHOICES.t2f
        return None

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

    def snapshot_additional_data(self, diff):
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
