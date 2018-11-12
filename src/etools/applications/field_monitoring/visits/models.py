from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel

from etools.applications.field_monitoring.planning.models import Task
from etools.applications.field_monitoring.settings.models import CheckListItem, MethodType, CPOutputConfig
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.publics.models import SoftDeleteMixin
from etools.applications.reports.models import Result
from etools.applications.utils.common.models.mixins import InheritedModelMixin


class FindingMixin(object):
    FINDING_CHOICES = Choices(
        ('y', _('As Planned')),
        ('n', _('Not As Planned')),
    )

    finding_value = models.CharField(max_length=1, blank=True, choices=FINDING_CHOICES, verbose_name=_('Finding'))
    finding_description = models.TextField(blank=True, verbose_name=_('Description'))
    finding_attachments = GenericRelation('attachments.Attachment', verbose_name=_('Attachments'), blank=True)


class VisitTaskLink(FindingMixin, models.Model):
    visit = models.ForeignKey('Visit', related_name=_('visit_task_links'))
    task = models.ForeignKey(Task, related_name=_('visit_task_links'))


class Visit(InheritedModelMixin, SoftDeleteMixin, TimeStampedModel):
    STATUS_CHOICES = Choices(
        ('draft', _('Draft')),
        ('assigned', _('Assigned')),
        ('finalized', _('Finalized')),
        ('cancelled', _('Cancelled')),
    )

    STATUSES_DATES = {
        STATUS_CHOICES.draft: 'date_created',
        STATUS_CHOICES.assigned: 'date_assigned',
        STATUS_CHOICES.finalized: 'date_finalized',
        STATUS_CHOICES.cancelled: 'date_cancelled',
    }

    # to be used by frontend to know what's the type of the visit is presented
    visit_type = 'unknown'

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    primary_field_monitor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='fm_primary_visits',
                                              verbose_name=_('Primary Field Monitor'), blank=True, null=True)
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='fm_visits',
                                          verbose_name=_('Team Members'), blank=True)

    tasks = models.ManyToManyField(Task, related_name='visits', through=VisitTaskLink)

    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))

    status = FSMField(choices=STATUS_CHOICES, default=STATUS_CHOICES.draft, verbose_name=_('Status'))

    date_assigned = MonitorField(verbose_name=_('Date Visit Assigned'), null=True, blank=True, default=None,
                                 monitor='status', when=[STATUS_CHOICES.assigned])
    date_finalized = MonitorField(verbose_name=_('Date Visit Finalized'), null=True, blank=True, default=None,
                                  monitor='status', when=[STATUS_CHOICES.finalized])
    date_cancelled = MonitorField(verbose_name=_('Date Visit Cancelled'), null=True, blank=True, default=None,
                                  monitor='status', when=[STATUS_CHOICES.cancelled])

    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    objects = InheritanceManager()

    @property
    def date_created(self):
        return self.created.date()

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    @property
    def reference_number(self):
        return '{}/{}/{}/FMT'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )

    @transition(
        status, source=STATUS_CHOICES.draft, target=STATUS_CHOICES.assigned,
    )
    def assign(self):
        # todo: generate TaskCheckListItem and VisitMethodType
        pass

    @transition(
        status, source=STATUS_CHOICES.assigned, target=STATUS_CHOICES.finalized,
    )
    def finalize(self):
        pass

    @transition(
        status, source=[STATUS_CHOICES.draft, STATUS_CHOICES.assigned], target=STATUS_CHOICES.cancelled,
    )
    def cancel(self):
        pass


class UNICEFVisit(Visit):
    visit_type = 'unicef'


class TaskCheckListItem(FindingMixin, OrderedModel):
    parent_slug = models.CharField(max_length=50, verbose_name=_('Parent Slug'))
    visit_task = models.ForeignKey(VisitTaskLink, verbose_name=_('Task Link'))

    question_number = models.CharField(max_length=10, verbose_name=_('Question Number'))
    question_text = models.CharField(max_length=255, verbose_name=_('Question Text'))
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)

    methods = models.ManyToManyField(Method, verbose_name=_('Recommended Methods'))

    class Meta:
        ordering = ('visit_task', 'order',)

    def __str__(self):
        return '{} {}'.format(self.question_number, self.question_text)

    @property
    def parent(self):
        return CheckListItem.objects.filter(slug=self.parent_slug).first()


class VisitMethodType(models.Model):
    parent_slug = models.CharField(max_length=50, verbose_name=_('Parent Slug'))
    visit = models.ForeignKey(Visit, verbose_name=_('Visit'), related_name='method_types')
    cp_output = models.ForeignKey(Result, verbose_name=_('CP Output'), related_name='visit_method_types')
    name = models.CharField(verbose_name=_('Name'), max_length=300)
    is_recommended = models.BooleanField(default=False, verbose_name=_('Recommended'))

    @property
    def parent(self):
        return MethodType.objects.filter(slug=self.parent_slug).first()
