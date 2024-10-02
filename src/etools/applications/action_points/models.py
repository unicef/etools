from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.utils.translation import gettext_lazy as _

from django_comments.models import Comment
from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_snapshot.models import Activity

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.transitions.conditions import (
    ActionPointCompleteActionsTakenCheck,
    ActionPointHighPriorityCompleteAttachmentCheck,
)
from etools.applications.action_points.transitions.serializers.serializers import ActionPointCompleteSerializer
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.environment.notifications import send_notification_with_template
from etools.libraries.djangolib.models import GroupWrapper
from etools.libraries.djangolib.utils import get_environment
from etools.libraries.fsm.views import has_action_permission


class ActionPointComment(Comment):
    supporting_document = CodedGenericRelation(
        Attachment, verbose_name=_('Related Documents'), code='action_points_supporting_document', blank=True
    )

    class Meta:
        proxy = True
        verbose_name = _('Action Point Comment')
        verbose_name_plural = _('Action Point Comments')


class ActionPointManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('author',
                                                       'section', 'office', 'location', 'partner',
                                                       'cp_output__result_type', 'engagement', 'intervention')\
            .select_related('assigned_to', "assigned_by", "category")


class ActionPoint(TimeStampedModel):
    MODULE_CHOICES = Category.MODULE_CHOICES

    STATUS_OPEN = 'open'
    STATUS_COMPLETED = 'completed'

    STATUSES = Choices(
        (STATUS_OPEN, _('Open')),
        (STATUS_COMPLETED, _('Completed')),
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
                               verbose_name=_('Author'), on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', verbose_name=_('Assigned By'),
                                    on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_action_points',
                                    verbose_name=_('Assigned To'), on_delete=models.CASCADE)
    status = FSMField(verbose_name=_('Status'), max_length=10, choices=STATUSES, default=STATUSES.open, protected=True)
    category = models.ForeignKey(Category, verbose_name=_('Category'), blank=True, null=True, on_delete=models.CASCADE)
    description = models.TextField(verbose_name=_('Description'))
    due_date = models.DateField(verbose_name=_('Due Date'), blank=True, null=True)
    high_priority = models.BooleanField(default=False, verbose_name=_('High Priority'))
    section = models.ForeignKey('reports.Section', verbose_name=_('Section'), blank=True, null=True,
                                on_delete=models.CASCADE)
    office = models.ForeignKey('reports.Office', verbose_name=_('Office'), blank=True, null=True,
                               on_delete=models.CASCADE)
    location = models.ForeignKey('locations.Location', verbose_name=_('Location'), blank=True, null=True,
                                 on_delete=models.CASCADE)
    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Partner'), blank=True, null=True,
                                on_delete=models.CASCADE)
    cp_output = models.ForeignKey('reports.Result', verbose_name=_('CP Output'), blank=True, null=True,
                                  on_delete=models.CASCADE)
    intervention = models.ForeignKey('partners.Intervention', verbose_name=_('PD/SPD'), blank=True, null=True,
                                     on_delete=models.CASCADE)
    engagement = models.ForeignKey('audit.Engagement', verbose_name=_('Engagement'), blank=True, null=True,
                                   related_name='action_points', on_delete=models.CASCADE)
    psea_assessment = models.ForeignKey('psea.Assessment', verbose_name=_('PSEA Assessment'), blank=True, null=True,
                                        related_name='action_points', on_delete=models.CASCADE)
    tpm_activity = models.ForeignKey('tpm.TPMActivity', verbose_name=_('TPM Activity'), blank=True, null=True,
                                     related_name='action_points', on_delete=models.CASCADE)
    travel_activity = models.ForeignKey('t2f.TravelActivity', verbose_name=_('Travel Activity'), blank=True, null=True,
                                        on_delete=models.CASCADE)
    monitoring_activity = models.ForeignKey('field_monitoring_planning.MonitoringActivity',
                                            verbose_name=_('Monitoring Activity'), blank=True, null=True,
                                            on_delete=models.CASCADE)
    date_of_completion = MonitorField(verbose_name=_('Date Action Point Completed'), null=True, blank=True,
                                      default=None, monitor='status', when=[STATUSES.completed])
    date_of_verification = MonitorField(verbose_name=_('Date Action Point Verified'), null=True, blank=True,
                                        default=None, monitor='verified_by')
    comments = GenericRelation(ActionPointComment, object_id_field='object_pk')
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')
    reference_number = models.CharField(
        verbose_name=_("Reference Number"),
        max_length=100,
        null=True,
    )

    # verification
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='verified_action_points',
                                    verbose_name=_('Verified By'), on_delete=models.CASCADE, blank=True, null=True)
    is_adequate = models.BooleanField(default=False, verbose_name=_('Is Adequate'))
    potential_verifier = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='action_points_to_verify',
                                           verbose_name=_('Potential Verifier'), on_delete=models.CASCADE,
                                           blank=True, null=True)

    tracker = FieldTracker(fields=['assigned_to', 'reference_number'])

    objects = ActionPointManager()

    class Meta:
        ordering = ('id', )
        verbose_name = _('Action Point')
        verbose_name_plural = _('Action Points')

    @property
    def engagement_subclass(self):
        return self.engagement.get_subclass() if self.engagement else None

    @property
    def related_object(self):
        related_object = self.engagement_subclass or self.tpm_activity or self.travel_activity
        related_object = related_object or self.psea_assessment or self.monitoring_activity
        return related_object

    @property
    def related_object_str(self):
        obj = self.related_object
        if not obj:
            return

        if self.tpm_activity:
            return 'Task No {0} for Visit {1}'.format(obj.task_number, obj.tpm_visit.reference_number)

        elif self.travel_activity:
            if self.travel_activity.travel:
                return 'Task No {0} for Visit {1}'.format(obj.task_number, obj.travel.reference_number)
            else:
                return 'Task not assigned to Visit'

        return str(obj)

    @property
    def related_object_url(self):
        obj = self.related_object
        if not obj:
            return

        return obj.get_object_url()

    @property
    def related_module(self):
        if self.engagement:
            return self.MODULE_CHOICES.audit
        elif self.tpm_activity:
            return self.MODULE_CHOICES.tpm
        elif self.travel_activity:
            return self.MODULE_CHOICES.t2f
        elif self.psea_assessment:
            return self.MODULE_CHOICES.psea
        elif self.monitoring_activity:
            return self.MODULE_CHOICES.fm
        return self.MODULE_CHOICES.apd

    def get_reference_number(self):
        if self.reference_number:
            return self.reference_number
        return '{}/{}/{}/APD'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference_number:
            self.reference_number = self.get_reference_number()
            self.save()

    def get_object_url(self, **kwargs):
        return build_frontend_url('apd', 'action-points', 'detail', self.id, **kwargs)

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    def __str__(self):
        return self.reference_number

    def get_meaningful_history(self):
        return self.history.filter(
            models.Q(action=Activity.CREATE) | models.Q(models.Q(action=Activity.UPDATE), ~models.Q(change={})))

    def snapshot_additional_data(self, diff):
        key_events = []
        if 'status' in diff:
            key_events.append(self.KEY_EVENTS.status_update)
        if 'assigned_to' in diff:
            key_events.append(self.KEY_EVENTS.reassign)

        return {'key_events': key_events}

    @classmethod
    def get_snapshot_action_display(cls, activity):
        key_events = activity.data.get('key_events')
        if key_events:
            if cls.KEY_EVENTS.status_update in key_events:
                return cls.STATUSES[activity.change['status']['after']]
            elif cls.KEY_EVENTS.reassign in key_events:
                return _('Reassigned to {}').format(
                    get_user_model().objects.get(pk=activity.change['assigned_to']['after']).get_full_name()
                )

        return activity.get_action_display()

    def get_mail_context(self, user=None):
        return {
            'person_responsible': self.assigned_to.get_full_name(),
            'assigned_by': self.assigned_by.get_full_name(),
            'reference_number': self.get_reference_number(),
            'partner': self.partner.name if self.partner else '',
            'description': self.description,
            'due_date': self.due_date.strftime('%d %b %Y') if self.due_date else '',
            'status': self.status,
            'object_url': self.get_object_url(user=user),
        }

    def send_email(self, recipient, template_name, additional_context=None, cc=None):

        context = {
            'environment': get_environment(),
            'action_point': self.get_mail_context(user=recipient),
            'recipient': recipient.get_full_name(),
        }
        context.update(additional_context or {})

        send_notification_with_template(
            recipients=recipient.email,
            template_name=template_name,
            context=context,
            sender=self,
            cc=cc,
        )

    def _do_complete(self, completed_by=None):
        if self.potential_verifier:
            self.send_email(
                self.potential_verifier,
                'action_points/action_point/action_point-available-for-verification',
            )
        self.send_email(self.assigned_by, 'action_points/action_point/completed', cc=[self.assigned_to.email],
                        additional_context={'completed_by': (completed_by or self.assigned_to).get_full_name()})

    @transition(status, source=STATUSES.open, target=STATUSES.completed,
                permission=has_action_permission(action='complete'),
                conditions=[
                    ActionPointCompleteActionsTakenCheck.as_condition(),
                    ActionPointHighPriorityCompleteAttachmentCheck.as_condition()
                ],
                custom={'serializer': ActionPointCompleteSerializer})
    def complete(self, completed_by=None, potential_verifier=None):
        if potential_verifier:
            self.potential_verifier = potential_verifier
        self._do_complete(completed_by=completed_by)


PME = GroupWrapper(code='pme',
                   name='PME')

OperationsGroup = GroupWrapper(code='operations',
                               name='Operations')

UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')
