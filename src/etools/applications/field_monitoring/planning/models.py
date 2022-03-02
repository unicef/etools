from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.db.models import Count, Exists, OuterRef, Q
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_locations.models import Location

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.field_monitoring.data_collection.offline.synchronizer import (
    MonitoringActivityOfflineSynchronizer,
)
from etools.applications.field_monitoring.fm_settings.models import LocationSite, Method, Question
from etools.applications.field_monitoring.planning.mixins import ProtectUnknownTransitionsMeta
from etools.applications.field_monitoring.planning.transitions.permissions import (
    user_is_field_monitor_permission,
    user_is_pme_permission,
    user_is_visit_lead_permission,
)
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, Section
from etools.applications.tpm.models import PME
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
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('CP Output'),
                                  on_delete=models.CASCADE, related_name='+')
    intervention = models.ForeignKey(Intervention, blank=True, null=True, verbose_name=_('Intervention'),
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


class MonitoringActivitiesQuerySet(models.QuerySet):
    def filter_hact_for_partner(self, partner_id: int):
        from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding

        question_sq = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity_id=OuterRef('id'),
            activity_question__is_hact=True,
            activity_question__question__level='partner',
            value__isnull=False,
        )
        # an overall finding for the partner is not requried for hact, leaving the code in for now in case
        # the business owners want to change
        # finding_sq = ActivityOverallFinding.objects.filter(
        #     ~Q(narrative_finding=''),
        #     monitoring_activity_id=OuterRef('id'),
        #     partner_id=partner_id,
        # )

        return self.annotate(
            is_hact=Exists(question_sq),
            # has_finding_for_partner=Exists(finding_sq),
        ).filter(
            partners=partner_id,
            status=MonitoringActivity.STATUS_COMPLETED,
            is_hact=True,
            # has_finding_for_partner=True,
        )


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

    STATUS_DRAFT = 'draft'
    STATUS_CHECKLIST = 'checklist'
    STATUS_REVIEW = 'review'
    STATUS_ASSIGNED = 'assigned'
    STATUS_DATA_COLLECTION = 'data_collection'
    STATUS_REPORT_FINALIZATION = 'report_finalization'
    STATUS_SUBMITTED = 'submitted'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUSES = Choices(
        (STATUS_DRAFT, _('Draft')),
        (STATUS_CHECKLIST, _('Checklist')),
        (STATUS_REVIEW, _('Review')),
        (STATUS_ASSIGNED, _('Assigned')),
        (STATUS_DATA_COLLECTION, _('Data Collection')),
        (STATUS_REPORT_FINALIZATION, _('Report Finalization')),
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_COMPLETED, _('Completed')),
        (STATUS_CANCELLED, _('Cancelled')),
    )
    TPM_AVAILABLE_STATUSES = [
        STATUSES.assigned,
        STATUSES.data_collection,
        STATUSES.report_finalization,
        STATUSES.submitted,
        STATUSES.completed,
    ]

    TRANSITION_SIDE_EFFECTS = {
        STATUSES.draft: [
            lambda i, old_instance=None, user=None: i.check_if_rejected(old_instance),
        ],
        STATUSES.checklist: [
            lambda i, old_instance=None, user=None: i.prepare_questions_structure(old_instance.status),
        ],
        STATUSES.review: [
            lambda i, old_instance=None, user=None: i.prepare_activity_overall_findings(),
            lambda i, old_instance=None, user=None: i.prepare_questions_overall_findings(),
        ],
        STATUSES.assigned: [
            lambda i, old_instance=None, user=None: i.auto_accept_staff_activity(old_instance),
        ],
        STATUSES.data_collection: [
            lambda i, old_instance=None, user=None: i.init_offline_blueprints(),
        ],
        STATUSES.report_finalization: [
            lambda i, old_instance=None, user=None: i.close_offline_blueprints(),
            lambda i, old_instance=None, user=None: i.port_findings_to_summary(),
        ],
        STATUSES.submitted: [
            lambda i, old_instance=None, user=None: i.send_submit_notice(),
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
    visit_lead = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                   verbose_name=_('Person Responsible'), related_name='+',
                                   on_delete=models.SET_NULL)

    field_office = models.ForeignKey('reports.Office', blank=True, null=True, verbose_name=_('Field Office'),
                                     on_delete=models.CASCADE)
    offices = models.ManyToManyField('reports.Office', blank=True, verbose_name=_('Field Offices'),
                                     related_name='offices')
    sections = models.ManyToManyField(Section, blank=True, verbose_name=_('Sections'))

    location = models.ForeignKey(Location, verbose_name=_('Location'), related_name='monitoring_activities',
                                 blank=True, null=True, on_delete=models.CASCADE)
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      related_name='monitoring_activities', on_delete=models.CASCADE)

    partners = models.ManyToManyField(PartnerOrganization, verbose_name=_('Partner'),
                                      related_name='monitoring_activities', blank=True)
    interventions = models.ManyToManyField(Intervention, related_name='monitoring_activities',
                                           blank=True, verbose_name=_('PD/SPD'))
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

    visit_lead_tracker = FieldTracker(fields=['visit_lead'])

    objects = models.Manager.from_queryset(MonitoringActivitiesQuerySet)()

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

    def check_if_rejected(self, old_instance):
        # if rejected send notice
        if old_instance and old_instance.status == self.STATUSES.assigned:
            email_template = "fm/activity/reject"
            recipients = PME.as_group().user_set.filter(
                profile__country=connection.tenant,
            )
            for recipient in recipients:
                self._send_email(
                    recipient.email,
                    email_template,
                    context={'recipient': recipient.get_full_name()},
                    user=recipient
                )

    def send_submit_notice(self):
        recipients = PME.as_group().user_set.filter(
            profile__country=connection.tenant,
        )
        if self.monitor_type == self.MONITOR_TYPE_CHOICES.staff:
            email_template = 'fm/activity/staff-submit'
        else:
            email_template = 'fm/activity/submit'
        for recipient in recipients:
            self._send_email(
                recipient.email,
                email_template,
                context={'recipient': recipient.get_full_name()},
                user=recipient
            )

    def prepare_questions_structure(self, old_status=STATUSES.draft):
        if old_status != self.STATUSES.draft:
            # do nothing if we just moved back from review
            return

        # cleanup
        self.questions.all().delete()

        from etools.applications.field_monitoring.data_collection.models import ActivityQuestion

        applicable_questions = Question.objects.filter(is_active=True).distinct()
        if self.sections.exists():
            applicable_questions = applicable_questions.filter(
                Q(sections__in=self.sections.values_list('pk', flat=True)) |
                Q(sections__isnull=True))

        questions = []

        for relation, level in self.RELATIONS_MAPPING:
            for target in getattr(self, relation).all():
                target_questions = applicable_questions.filter(level=level).prefetch_templates(
                    level, target_id=target.id
                )
                for target_question in target_questions:
                    activity_question = ActivityQuestion(
                        question=target_question, monitoring_activity=self,
                        text=target_question.text, is_hact=target_question.is_hact,
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
            'visit_lead': self.visit_lead.get_full_name(),
            'reference_number': self.number,
            'location_name': self.location.name,
            'vendor_name': self.tpm_partner.name if self.tpm_partner else None,
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
                permission=user_is_visit_lead_permission)
    def accept(self):
        pass

    def auto_accept_staff_activity(self, old_instance):
        # send email to users assigned to fm activity
        recipients = set(
            list(self.team_members.all()) + [self.visit_lead]
        )
        # check if it was rejected otherwise send assign message
        if old_instance and old_instance.status == self.STATUSES.submitted:
            email_template = "fm/activity/staff-reject"
            recipients = [self.visit_lead]
        elif self.monitor_type == self.MONITOR_TYPE_CHOICES.staff:
            email_template = 'fm/activity/staff-assign'
        else:
            email_template = 'fm/activity/assign'
        for recipient in recipients:
            self._send_email(
                recipient.email,
                email_template,
                context={'recipient': recipient.get_full_name()},
                user=recipient
            )

        if self.monitor_type == self.MONITOR_TYPE_CHOICES.staff:
            self.accept()
            self.save()
            # todo: direct transitions doesn't trigger side effects.
            # trigger effects manually? or rewrite this effect?
            self.init_offline_blueprints()

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.draft,
                permission=user_is_visit_lead_permission)
    def reject(self):
        pass

    @transition(field=status, source=STATUSES.data_collection, target=STATUSES.report_finalization,
                permission=user_is_visit_lead_permission)
    def mark_data_collected(self):
        pass

    @transition(field=status, source=STATUSES.report_finalization, target=STATUSES.data_collection,
                permission=user_is_visit_lead_permission)
    def revert_data_collected(self):
        pass

    @transition(field=status, source=STATUSES.report_finalization, target=STATUSES.submitted,
                permission=user_is_visit_lead_permission)
    def submit_report(self):
        pass

    @transition(field=status, source=STATUSES.submitted, target=STATUSES.completed,
                permission=user_is_pme_permission)
    def complete(self):
        pass

    @transition(field=status, source=STATUSES.submitted, target=STATUSES.report_finalization,
                permission=user_is_pme_permission)
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
            partner_org.update_programmatic_visits(event_date=self.end_date, update_one=True)

    def init_offline_blueprints(self):
        MonitoringActivityOfflineSynchronizer(self).initialize_blueprints()

    def close_offline_blueprints(self):
        MonitoringActivityOfflineSynchronizer(self).close_blueprints()

    def port_findings_to_summary(self):
        from etools.applications.field_monitoring.data_collection.models import ChecklistOverallFinding

        valid_questions = self.questions.annotate(
            answers_count=Count('findings', filter=Q(findings__value__isnull=False)),
        ).filter(answers_count=1).prefetch_related('findings')
        for question in valid_questions:
            question.overall_finding.value = question.findings.all()[0].value
            question.overall_finding.save()

        for overall_finding in self.overall_findings.all():
            narrative_findings = ChecklistOverallFinding.objects.filter(
                ~Q(narrative_finding=''),
                started_checklist__monitoring_activity=self,
                partner=overall_finding.partner,
                cp_output=overall_finding.cp_output,
                intervention=overall_finding.intervention,
            ).values_list('narrative_finding', flat=True)
            if len(narrative_findings) == 1:
                overall_finding.narrative_finding = narrative_findings[0]
                overall_finding.save()


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


class MonitoringActivityGroup(models.Model):
    partner = models.ForeignKey(
        'partners.PartnerOrganization',
        on_delete=models.CASCADE,
        related_name='monitoring_activity_groups',
    )
    monitoring_activities = models.ManyToManyField(MonitoringActivity, related_name='groups')

    def __str__(self):
        return f'{self.partner} Monitoring Activities Group'
