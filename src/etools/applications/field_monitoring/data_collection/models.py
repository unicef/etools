from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.field_monitoring.fm_settings.models import Method, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTargetMixin


class ActivityQuestion(QuestionTargetMixin, models.Model):
    monitoring_activity = models.ForeignKey(MonitoringActivity, related_name='questions', verbose_name=_('Activity'),
                                            on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='activity_questions', verbose_name=_('Question'),
                                 on_delete=models.CASCADE)
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)
    is_enabled = models.BooleanField(verbose_name=_('Enabled'), default=True)

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


class Finding(models.Model):
    started_checklist = models.ForeignKey(StartedChecklist, related_name='findings', verbose_name=_('Checklist'),
                                          on_delete=models.CASCADE)
    activity_question = models.ForeignKey(ActivityQuestion, related_name='findings',
                                          verbose_name=_('Activity Question'), on_delete=models.CASCADE)
    value = JSONField(null=True, blank=True, verbose_name=_('Value'))

    class Meta:
        verbose_name = _('Checklist Finding')
        verbose_name_plural = _('Checklist Findings')
        ordering = ('started_checklist', 'id',)

    def __str__(self):
        return '{}: {} - {}'.format(self.started_checklist, self.activity_question, self.value)


class ActivityQuestionOverallFinding(models.Model):
    activity_question = models.OneToOneField(ActivityQuestion, related_name='overall_finding',
                                             verbose_name=_('Activity'), on_delete=models.CASCADE)
    value = JSONField(null=True, blank=True, verbose_name=_('Value'))

    class Meta:
        verbose_name = _('Overall Activity Question Finding')
        verbose_name_plural = _('Overall Activity Question Findings')
        ordering = ('id',)

    def __str__(self):
        return '{} - {}'.format(self.activity_question, self.value)


class ChecklistOverallFinding(QuestionTargetMixin, models.Model):
    started_checklist = models.ForeignKey(StartedChecklist, related_name='overall_findings',
                                          verbose_name=_('Checklist'), on_delete=models.CASCADE)
    narrative_finding = models.TextField(blank=True, verbose_name=_('Narrative Finding'))
    attachments = CodedGenericRelation(Attachment, code='attachments', verbose_name=_('Attachments'), blank=True)

    class Meta:
        verbose_name = _('Checklist Overall Finding')
        verbose_name_plural = _('Checklist Overall Findings')
        ordering = ('started_checklist', 'id',)

    def __str__(self):
        return '{} - {}'.format(self.started_checklist, self.narrative_finding)


class ActivityOverallFinding(QuestionTargetMixin, models.Model):
    monitoring_activity = models.ForeignKey(MonitoringActivity, related_name='overall_findings',
                                            verbose_name=_('Activity'), on_delete=models.CASCADE)
    narrative_finding = models.TextField(blank=True, verbose_name=_('Narrative Finding'))
    on_track = models.NullBooleanField()

    class Meta:
        verbose_name = _('Activity Overall Finding')
        verbose_name_plural = _('Activity Overall Findings')
        ordering = ('monitoring_activity', 'id',)

    def __str__(self):
        return '{} - {}'.format(self.monitoring_activity, self.narrative_finding)
