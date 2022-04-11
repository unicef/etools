from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.field_monitoring.fm_settings.models import Method, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTargetMixin


class ActivityQuestionQuerySet(models.QuerySet):
    def filter_for_activity_export(self):
        return self.filter(is_enabled=True) \
            .select_related('question') \
            .annotate(entity_name=models.Case(
                models.When(cp_output__isnull=False,
                            then=models.F('cp_output__name')),
                models.When(partner__isnull=False,
                            then=models.F('partner__name')),
                output_field=models.TextField()))


class ActivityQuestion(QuestionTargetMixin, models.Model):
    monitoring_activity = models.ForeignKey(MonitoringActivity, related_name='questions', verbose_name=_('Activity'),
                                            on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='activity_questions', verbose_name=_('Question'),
                                 on_delete=models.CASCADE)

    """copy important fields from question to safely allow future question edits"""
    text = models.TextField(verbose_name=_('Question Text'))
    is_hact = models.BooleanField(default=False, verbose_name=_('Count as HACT'))

    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)
    is_enabled = models.BooleanField(verbose_name=_('Enabled'), default=True)

    objects = models.Manager.from_queryset(ActivityQuestionQuerySet)()

    class Meta:
        verbose_name = _('Activity Question')
        verbose_name_plural = _('Activity Questions')
        ordering = ('monitoring_activity', 'id',)

    def __str__(self):
        return '{}: {}'.format(self.monitoring_activity, self.question)


class StartedChecklist(models.Model):
    monitoring_activity = models.ForeignKey(MonitoringActivity, related_name='checklists', verbose_name=_('Activity'),
                                            on_delete=models.PROTECT)
    method = models.ForeignKey(Method, related_name='checklists', verbose_name=_('Methods'), on_delete=models.PROTECT)
    information_source = models.CharField(max_length=100, verbose_name=_('Information Source'), blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='checklists', verbose_name=_('Author'),
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Started Checklist')
        verbose_name_plural = _('Started Checklists')
        ordering = ('id',)

    def __str__(self):
        return 'Checklist {} for {}'.format(self.id, self.monitoring_activity)

    def prepare_findings(self):
        Finding.objects.bulk_create([
            Finding(started_checklist=self, activity_question=question)
            for question in self.monitoring_activity.questions.filter(
                is_enabled=True, question__methods=self.method
            ).distinct()
        ])

    def prepare_overall_findings(self):
        findings = []
        for relation, level in self.monitoring_activity.RELATIONS_MAPPING:
            for target in getattr(self.monitoring_activity, relation).all():
                if not self.monitoring_activity.questions.filter(
                    **{Question.get_target_relation_name(level): target},
                    is_enabled=True, question__methods=self.method
                ).exists():
                    continue

                finding = ChecklistOverallFinding(started_checklist=self)
                setattr(finding, Question.get_target_relation_name(level), target)

                findings.append(finding)

        ChecklistOverallFinding.objects.bulk_create(findings)

    def save(self, **kwargs):
        create = not self.pk
        super().save(**kwargs)
        if create:
            self.prepare_findings()
            self.prepare_overall_findings()


class FindingQuerySet(models.QuerySet):
    def filter_for_activity_export(self):
        return self.filter(
            activity_question__is_enabled=True) \
            .annotate(entity_name=models.Case(
                models.When(activity_question__cp_output__isnull=False,
                            then=models.F('activity_question__cp_output__name')),
                models.When(activity_question__partner__isnull=False,
                            then=models.F('activity_question__partner__name')),
                output_field=models.TextField()))


class Finding(models.Model):
    started_checklist = models.ForeignKey(StartedChecklist, related_name='findings', verbose_name=_('Checklist'),
                                          on_delete=models.CASCADE)
    activity_question = models.ForeignKey(ActivityQuestion, related_name='findings',
                                          verbose_name=_('Activity Question'), on_delete=models.CASCADE)
    value = models.JSONField(null=True, blank=True, verbose_name=_('Value'))

    objects = models.Manager.from_queryset(FindingQuerySet)()

    class Meta:
        verbose_name = _('Checklist Finding')
        verbose_name_plural = _('Checklist Findings')
        ordering = ('started_checklist', 'id',)

    def __str__(self):
        return '{}: {} - {}'.format(self.started_checklist, self.activity_question, self.value)


class ActivityQuestionOverallFinding(models.Model):
    """
        This model refers to the answer provided for a question during the 'summary analysis'
        in the case where the related activity_question.question is marked as 'is_hact' then this, answer not being
        null, reflects that the related monitoring activity (activity_question.monitoring_activity) will count as a
        programmatic visit for the partner
    """
    activity_question = models.OneToOneField(ActivityQuestion, related_name='overall_finding',
                                             verbose_name=_('Activity'), on_delete=models.CASCADE)
    value = models.JSONField(null=True, blank=True, verbose_name=_('Value'))

    class Meta:
        verbose_name = _('Overall Activity Question Finding')
        verbose_name_plural = _('Overall Activity Question Findings')
        ordering = ('id',)

    def __str__(self):
        return '{} - {}'.format(self.activity_question, self.value)


class ChecklistOverallFindingQuerySet(models.QuerySet):
    def annotate_for_activity_export(self):
        return self.annotate(entity_name=models.Case(
            models.When(cp_output__isnull=False, then=models.F('cp_output__name')),
            models.When(partner__isnull=False, then=models.F('partner__name')),
            output_field=models.TextField()))


class ChecklistOverallFinding(QuestionTargetMixin, models.Model):
    started_checklist = models.ForeignKey(StartedChecklist, related_name='overall_findings',
                                          verbose_name=_('Checklist'), on_delete=models.CASCADE)
    narrative_finding = models.TextField(blank=True, verbose_name=_('Narrative Finding'))
    attachments = CodedGenericRelation(Attachment, code='attachments', verbose_name=_('Attachments'), blank=True)

    objects = models.Manager.from_queryset(ChecklistOverallFindingQuerySet)()

    class Meta:
        verbose_name = _('Checklist Overall Finding')
        verbose_name_plural = _('Checklist Overall Findings')
        ordering = ('started_checklist', 'id',)

    def __str__(self):
        return '{} - {}'.format(self.started_checklist, self.narrative_finding)


class ActivityOverallFindingQuerySet(models.QuerySet):
    def annotate_for_activity_export(self):
        return self.annotate(entity_name=models.Case(
            models.When(cp_output__isnull=False, then=models.F('cp_output__name')),
            models.When(partner__isnull=False, then=models.F('partner__name')),
            output_field=models.TextField()))


class ActivityOverallFinding(QuestionTargetMixin, models.Model):
    monitoring_activity = models.ForeignKey(MonitoringActivity, related_name='overall_findings',
                                            verbose_name=_('Activity'), on_delete=models.CASCADE)
    narrative_finding = models.TextField(blank=True, verbose_name=_('Narrative Finding'))
    on_track = models.BooleanField(null=True, blank=True)

    objects = models.Manager.from_queryset(ActivityOverallFindingQuerySet)()

    class Meta:
        verbose_name = _('Activity Overall Finding')
        verbose_name_plural = _('Activity Overall Findings')
        ordering = ('monitoring_activity', 'id',)

    def __str__(self):
        return '{} - {}'.format(self.monitoring_activity, self.narrative_finding)
