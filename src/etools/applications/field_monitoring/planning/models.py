from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_locations.models import Location

from etools.applications.core.permissions import import_permissions
from etools.applications.field_monitoring.fm_settings.models import LocationSite, Question
from etools.applications.field_monitoring.planning.mixins import ProtectUnknownTransitionsMeta
from etools.applications.field_monitoring.planning.transitions.permissions import (
    user_is_field_monitor_permission,
    user_is_person_responsible_permission,
)
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, Section
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.users.models import Office
from etools.libraries.djangolib.models import SoftDeleteMixin


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
    TYPES = Choices(
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

    TRANSITION_SIDE_EFFECTS = {
        'checklist': [
            lambda i, old_instance=None, user=None: i.prepare_questions_structure(),
        ],
        'review': [
            lambda i, old_instance=None, user=None: i.prepare_activity_overall_findings(),
            lambda i, old_instance=None, user=None: i.prepare_questions_overall_findings(),
        ],
        'assigned': [
            lambda i, old_instance=None, user=None: i.auto_accept_staff_activity(),
        ]
    }

    AUTO_TRANSITIONS = {}

    RELATIONS_MAPPING = (
        ('partners', 'partner'),
        ('cp_outputs', 'output'),
        ('interventions', 'intervention'),
    )

    activity_type = models.CharField(max_length=10, choices=TYPES, default=TYPES.staff)

    tpm_partner = models.ForeignKey(TPMPartner, blank=True, null=True, verbose_name=_('TPM Partner'),
                                    on_delete=models.CASCADE)
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Team Members'),
                                          related_name='monitoring_activities')
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                           verbose_name=_('Person Responsible'), related_name='+',
                                           on_delete=models.SET_NULL)

    field_office = models.ForeignKey(Office, blank=True, null=True, verbose_name=_('Field Office'),
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
    cancel_reason = models.TextField(verbose_name=_('Cancellation reason'), blank=True)

    class Meta:
        verbose_name = _('Monitoring Activity')
        verbose_name_plural = _('Monitoring Activities')
        ordering = ('id',)

    def __str__(self):
        return self.reference_number

    @property
    def reference_number(self):
        return '{}/{}/{}/FMA'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def prepare_questions_structure(self):
        # cleanup
        self.questions.all().delete()

        from etools.applications.field_monitoring.data_collection.models import ActivityQuestion

        applicable_questions = Question.objects.filter(
            sections__in=self.sections.values_list('pk', flat=True), is_active=True
        ).distinct()
        questions = []

        for relation, level in self.RELATIONS_MAPPING:
            for target in getattr(self, relation).all():
                target_questions = applicable_questions.filter(level=level).prefetch_templates(
                    level, target_id=target.id
                )
                for target_question in target_questions:
                    activity_question = ActivityQuestion(question=target_question, monitoring_activity=self)

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
                finding = ActivityOverallFinding(monitoring_activity=self)

                setattr(finding, Question.get_target_relation_name(level), target)

                findings.append(finding)

        ActivityOverallFinding.objects.bulk_create(findings)

    def prepare_questions_overall_findings(self):
        from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding

        ActivityQuestionOverallFinding.objects.bulk_create([
            ActivityQuestionOverallFinding(activity_question=question)
            for question in self.questions.filter(is_enabled=True)
        ])

    @transition(field=status, source=STATUSES.draft, target=STATUSES.checklist,
                permission=user_is_field_monitor_permission)
    def mark_details_configured(self):
        self.prepare_questions_structure()

    @transition(field=status, source=STATUSES.checklist, target=STATUSES.draft,
                permission=user_is_field_monitor_permission)
    def revert_details_configured(self):
        pass

    @transition(field=status, source=STATUSES.checklist, target=STATUSES.review,
                permission=user_is_field_monitor_permission)
    def mark_checklist_configured(self):
        self.prepare_activity_overall_findings()
        self.prepare_questions_overall_findings()

    @transition(field=status, source=STATUSES.review, target=STATUSES.checklist,
                permission=user_is_field_monitor_permission)
    def revert_checklist_configured(self):
        pass

    @transition(field=status, source=STATUSES.review, target=STATUSES.assigned,
                permission=user_is_field_monitor_permission)
    def assign(self):
        pass

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.review,
                permission=user_is_field_monitor_permission)
    def revert_assign(self):
        pass

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.data_collection,
                permission=user_is_person_responsible_permission)
    def accept(self):
        pass

    def auto_accept_staff_activity(self):
        if self.activity_type == self.TYPES.staff:
            self.accept()
            self.save()

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
        return self.questions.filter(is_enabled=True)

    @property
    def started_checklist_set(self):
        return self.checklists.exists()

    @property
    def activity_overall_finding(self):
        # todo: decide what to use as value here. all overall findings should be completed?
        return True

    @property
    def activity_question_overall_finding(self):
        # todo: see activity_overall_finding
        return True

    @property
    def action_points(self):
        return True
