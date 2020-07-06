from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_locations.models import Location
from unicef_notification.utils import send_notification_with_template

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.field_monitoring.data_collection.offline.synchronizer import (
    MonitoringActivityOfflineSynchronizer,
)
from etools.applications.field_monitoring.fm_settings.models import LocationSite, Method, Question
from etools.applications.field_monitoring.planning.mixins import ProtectUnknownTransitionsMeta
from etools.applications.field_monitoring.planning.transitions.permissions import (
    user_is_field_monitor_permission,
    user_is_person_responsible_permission,
)
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, Section
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.libraries.djangolib.models import SoftDeleteMixin
from etools.libraries.djangolib.utils import get_environment


class YearPlan(TimeStampedModel):
    year = models.PositiveSmallIntegerField(primary_key=True)

    prioritization_criteria = models.TextField(verbose_name=_('Prioritization Criteria'), blank=True)
    methodology_notes = models.TextField(verbose_name=_('Methodology Notes & Standards'), blank=True)
    target_visits = models.PositiveSmallIntegerField(verbose_name=_('Target Visits For The Year'),
                                                     blank=True, default=0)
    modalities = models.TextField(verbose_name=_('Modalities'), blank=True)
    partner_engagement = models.TextField(verbose_name=_('Partner Engagement'), blank=True)
    other_aspects = models.TextField(verbose_name=_('Other Aspects of the Field Monitoring Plan'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    class Meta:
        verbose_name = _('Year Plan')
        verbose_name_plural = _('Year Plans')
        ordering = ('year',)

    @classmethod
    def get_defaults(cls, year):
        previous_year_plan = cls._default_manager.filter(year=int(year) - 1).first()
        if not previous_year_plan:
            return {}

        return {
            field: getattr(previous_year_plan, field) for field in
            ['prioritization_criteria', 'methodology_notes', 'target_visits', 'modalities', 'partner_engagement']
            if getattr(previous_year_plan, field)
        }

    def __str__(self):
        return 'Year Plan for {}'.format(self.year)


class QuestionTargetMixin(models.Model):
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE, related_name='+')
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('Partner'),
                                  on_delete=models.CASCADE, related_name='+')
    intervention = models.ForeignKey(Intervention, blank=True, null=True, verbose_name=_('Partner'),
                                     on_delete=models.CASCADE, related_name='+')

    @property
    def related_to(self):
        return self.partner or self.cp_output or self.intervention

    class Meta:
        abstract = True


class QuestionTemplate(QuestionTargetMixin, models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_('Question'),
                                 related_name='templates')
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)

    class Meta:
        verbose_name = _('Question Template')
        verbose_name_plural = _('Question Templates')
        ordering = ('id',)

    def is_specific(self):
        return any([self.partner_id, self.cp_output_id, self.intervention_id])

    def __str__(self):
        return 'Question Template for {}'.format(self.related_to)


class MonitoringActivityMeta(ProtectUnknownTransitionsMeta, ModelBase):
    pass


class MonitoringActivity(
    SoftDeleteMixin,
    TimeStampedModel,
    models.Model,
    metaclass=MonitoringActivityMeta
):
    MONITOR_TYPE_CHOICES = Choices(
        ('staff', _('Staff')),
        ('tpm', _('TPM')),
    )

    STATUSES = Choices(
        ('draft', _('Draft')),
        ('checklist', _('Checklist')),
        ('review', _('Review')),
        ('assigned', _('Assigned')),
        ('data_collection', _('Data Collection')),
        ('report_finalization', _('Report Finalization')),
        ('submitted', _('Submitted')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )
    TPM_AVAILABLE_STATUSES = [
        STATUSES.assigned,
        STATUSES.data_collection,
        STATUSES.report_finalization,
        STATUSES.submitted,
        STATUSES.completed,
    ]

    TRANSITION_SIDE_EFFECTS = {
        STATUSES.checklist: [
            lambda i, old_instance=None, user=None: i.prepare_questions_structure(old_instance.status),
        ],
        STATUSES.review: [
            lambda i, old_instance=None, user=None: i.prepare_activity_overall_findings(),
            lambda i, old_instance=None, user=None: i.prepare_questions_overall_findings(),
        ],
        STATUSES.assigned: [
            lambda i, old_instance=None, user=None: i.auto_accept_staff_activity(),
        ],
        STATUSES.data_collection: [
            lambda i, old_instance=None, user=None: i.init_offline_blueprints(),
        ],
        STATUSES.report_finalization: [
            lambda i, old_instance=None, user=None: i.close_offline_blueprints(),
        ],
        STATUSES.completed: [
            lambda i, old_instance=None, user=None: i.update_one_hact_value(),
        ],
        STATUSES.cancelled: [
            lambda i, old_instance=None, user=None: i.close_offline_blueprints(),
        ],
    }

    AUTO_TRANSITIONS = {}

    RELATIONS_MAPPING = (
        ('partners', 'partner'),
        ('cp_outputs', 'output'),
        ('interventions', 'intervention'),
    )

    number = models.CharField(
        verbose_name=_('Reference Number'),
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        editable=False,
    )

    monitor_type = models.CharField(max_length=10, choices=MONITOR_TYPE_CHOICES, default=MONITOR_TYPE_CHOICES.staff)

    tpm_partner = models.ForeignKey(TPMPartner, blank=True, null=True, verbose_name=_('TPM Partner'),
                                    on_delete=models.CASCADE)
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Team Members'),
                                          related_name='monitoring_activities')
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                           verbose_name=_('Person Responsible'), related_name='+',
                                           on_delete=models.SET_NULL)

    field_office = models.ForeignKey('reports.Office', blank=True, null=True, verbose_name=_('Field Office'),
                                     on_delete=models.CASCADE)

    sections = models.ManyToManyField(Section, blank=True, verbose_name=_('Sections'))

    location = models.ForeignKey(Location, verbose_name=_('Location'), related_name='monitoring_activities',
                                 blank=True, null=True, on_delete=models.CASCADE)
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      related_name='monitoring_activities', on_delete=models.CASCADE)

    partners = models.ManyToManyField(PartnerOrganization, verbose_name=_('Partner'),
                                      related_name='monitoring_activities', blank=True)
    interventions = models.ManyToManyField(Intervention, related_name='monitoring_activities',
                                           blank=True, verbose_name=_('PD/SSFA'))
    cp_outputs = models.ManyToManyField(Result, verbose_name=_('Outputs'), related_name='monitoring_activities',
                                        blank=True)

    start_date = models.DateField(verbose_name=_('Start Date'), blank=True, null=True)
    end_date = models.DateField(verbose_name=_('End Date'), blank=True, null=True)

    status = FSMField(verbose_name=_('Status'), max_length=20, choices=STATUSES, default=STATUSES.draft)

    attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Attachments'),
                                       code='attachments', blank=True)
    report_attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Attachments'),
                                              code='report_attachments', blank=True)

    reject_reason = models.TextField(verbose_name=_('Rejection reason'), blank=True)
    report_reject_reason = models.TextField(verbose_name=_('Report rejection reason'), blank=True)
    cancel_reason = models.TextField(verbose_name=_('Cancellation reason'), blank=True)

    person_responsible_tracker = FieldTracker(fields=['person_responsible'])

    class Meta:
        verbose_name = _('Monitoring Activity')
        verbose_name_plural = _('Monitoring Activities')
        ordering = ('id',)

    def __str__(self):
        return self.reference_number

    def save(self, **kwargs):
        super().save(**kwargs)

        if not self.number:
            self.number = '{}/{}/{}/FMA'.format(
                connection.tenant.country_short_code or '',
                self.created.year,
                self.id,
            )
            super().save(update_fields=['number'])

    @property
    def reference_number(self):
        return self.number

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def prepare_questions_structure(self, old_status=STATUSES.draft):
        if old_status != self.STATUSES.draft:
            # do nothing if we just moved back from review
            return

        # cleanup
        self.questions.all().delete()

        from etools.applications.field_monitoring.data_collection.models import ActivityQuestion

        applicable_questions = Question.objects.filter(is_active=True).distinct()
        if self.sections.exists():
            applicable_questions = applicable_questions.filter(sections__in=self.sections.values_list('pk', flat=True))

        questions = []

        for relation, level in self.RELATIONS_MAPPING:
            for target in getattr(self, relation).all():
                target_questions = applicable_questions.filter(level=level).prefetch_templates(
                    level, target_id=target.id
                )
                for target_question in target_questions:
                    activity_question = ActivityQuestion(
                        question=target_question, monitoring_activity=self,
                        is_enabled=target_question.template.is_active if target_question.template else False
                    )

                    if target_question.template:
                        activity_question.specific_details = target_question.template.specific_details

                    setattr(activity_question, Question.get_target_relation_name(level), target)

                    questions.append(activity_question)

        ActivityQuestion.objects.bulk_create(questions)

    def prepare_activity_overall_findings(self):
        self.overall_findings.all().delete()

        from etools.applications.field_monitoring.data_collection.models import ActivityOverallFinding

        findings = []
        for relation, level in self.RELATIONS_MAPPING:
            for target in getattr(self, relation).all():
                if not self.questions.filter(**{Question.get_target_relation_name(level): target}).exists():
                    continue

                finding = ActivityOverallFinding(monitoring_activity=self)

                setattr(finding, Question.get_target_relation_name(level), target)

                findings.append(finding)

        ActivityOverallFinding.objects.bulk_create(findings)

    def prepare_questions_overall_findings(self):
        from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding

        # cleanup
        ActivityQuestionOverallFinding.objects.filter(activity_question__monitoring_activity=self).delete()

        ActivityQuestionOverallFinding.objects.bulk_create([
            ActivityQuestionOverallFinding(activity_question=question)
            for question in self.questions.filter(is_enabled=True)
        ])

    def get_object_url(self, **kwargs):
        return build_frontend_url(
            'fm',
            'activities',
            self.pk,
            'details',
            **kwargs,
        )

    def get_mail_context(self, user=None):
        object_url = self.get_object_url(user=user)

        context = {
            'object_url': object_url,
        }

        return context

    def _send_email(self, recipients, template_name, context=None, user=None, **kwargs):
        context = context or {}

        base_context = {
            'activity': self.get_mail_context(user=user),
            'environment': get_environment(),
        }
        base_context.update(context)
        context = base_context

        if isinstance(recipients, str):
            recipients = [recipients, ]
        else:
            recipients = list(recipients)

        # assert recipients
        if recipients:
            send_notification_with_template(
                recipients=recipients,
                template_name=template_name,
                context=context,
            )

    @transition(field=status, source=STATUSES.draft, target=STATUSES.checklist,
                permission=user_is_field_monitor_permission)
    def mark_details_configured(self):
        pass

    @transition(field=status, source=STATUSES.checklist, target=STATUSES.draft,
                permission=user_is_field_monitor_permission)
    def revert_details_configured(self):
        pass

    @transition(field=status, source=STATUSES.checklist, target=STATUSES.review,
                permission=user_is_field_monitor_permission)
    def mark_checklist_configured(self):
        pass

    @transition(field=status, source=STATUSES.review, target=STATUSES.checklist,
                permission=user_is_field_monitor_permission)
    def revert_checklist_configured(self):
        pass

    @transition(field=status, source=STATUSES.review, target=STATUSES.assigned,
                permission=user_is_field_monitor_permission)
    def assign(self):
        pass

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.data_collection,
                permission=user_is_person_responsible_permission)
    def accept(self):
        pass

    def auto_accept_staff_activity(self):
        if self.monitor_type == self.MONITOR_TYPE_CHOICES.staff:
            self.accept()
            self.save()
            # todo: direct transitions doesn't trigger side effects.
            # trigger effects manually? or rewrite this effect?
            self.init_offline_blueprints()

        # send email to users assigned to fm activity
        recipients = set(
            list(self.team_members.all()) + [self.person_responsible]
        )
        for recipient in recipients:
            self._send_email(
                recipient.email,
                'fm/activity/assign',
                context={'recipient': recipient.get_full_name()},
                user=recipient
            )

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.draft,
                permission=user_is_person_responsible_permission)
    def reject(self):
        pass

    @transition(field=status, source=STATUSES.data_collection, target=STATUSES.report_finalization,
                permission=user_is_person_responsible_permission)
    def mark_data_collected(self):
        pass

    @transition(field=status, source=STATUSES.report_finalization, target=STATUSES.data_collection,
                permission=user_is_person_responsible_permission)
    def revert_data_collected(self):
        pass

    @transition(field=status, source=STATUSES.report_finalization, target=STATUSES.submitted,
                permission=user_is_person_responsible_permission)
    def submit_report(self):
        pass

    @transition(field=status, source=STATUSES.submitted, target=STATUSES.completed,
                permission=user_is_field_monitor_permission)
    def complete(self):
        pass

    @transition(field=status, source=STATUSES.submitted, target=STATUSES.assigned,
                permission=user_is_field_monitor_permission)
    def reject_report(self):
        pass

    @transition(field=status, target=STATUSES.cancelled,
                source=[
                    STATUSES.draft, STATUSES.checklist, STATUSES.review,
                    STATUSES.assigned, STATUSES.data_collection, STATUSES.report_finalization
                ],
                permission=user_is_field_monitor_permission)
    def cancel(self):
        pass

    @property
    def activity_question_set(self):
        return self.questions.filter(is_enabled=True).exists()

    @property
    def started_checklist_set(self):
        return self.checklists.exists()

    @property
    def activity_overall_finding(self):
        # at least one overall finding completed
        return self.overall_findings.exclude(narrative_finding='').exists()

    @property
    def methods(self):
        return Method.objects.filter(
            pk__in=self.questions.filter(
                is_enabled=True
            ).values_list('question__methods', flat=True)
        )

    def update_one_hact_value(self):
        """
            Every time an activity transitions to completed, all Partners associated with that activity
            will increase the completed PV count if applicable
        """

        aq_qs = self.questions.filter(question__is_hact=True).filter(overall_finding__value__isnull=False)
        partner_orgs = [aq.partner for aq in aq_qs.all() if aq.partner]

        for partner_org in partner_orgs:
            partner_org.programmatic_visits(event_date=self.end_date, update_one=True)

    def init_offline_blueprints(self):
        MonitoringActivityOfflineSynchronizer(self).initialize_blueprints()

    def close_offline_blueprints(self):
        MonitoringActivityOfflineSynchronizer(self).close_blueprints()


class MonitoringActivityActionPointManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(monitoring_activity__isnull=False)


class MonitoringActivityActionPoint(ActionPoint):
    """
    This proxy class is for more easy permissions assigning.
    """
    objects = MonitoringActivityActionPointManager()

    class Meta(ActionPoint.Meta):
        verbose_name = _('Monitoring Activity Action Point')
        verbose_name_plural = _('Monitoring Activity Action Points')
        proxy = True

    def get_mail_context(self, user=None):
        context = super().get_mail_context(user=user)
        if self.monitoring_activity:
            context['monitoring_activity'] = self.monitoring_activity.get_mail_context(user=user)
        return context
