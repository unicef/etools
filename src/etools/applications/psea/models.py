from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.attachments.models import Attachment

from .fields import PSEARatingField


class PSEAIndicator(TimeStampedModel):
    text = models.TextField(verbose_name=_('Text'))
    details = models.TextField(verbose_name=_('Details'))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('PSEA Indicator')
        verbose_name_plural = _('PSEA Indicators')

    def __str__(self):
        return f'{self.text}'


class PSEAEvidence(TimeStampedModel):
    indicators = models.ManyToManyField(PSEAIndicator, verbose_name=_('Indicators'))
    description = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('PSEA Evidence')
        verbose_name_plural = _('PSEA Evidence')

    def __str__(self):
        return f'{self.text}'


class PSEA(TimeStampedModel):

    DRAFT = 'draft'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    SUBMITTED = 'submitted'
    FINAL = 'final'
    CANCELLED = 'cancelled'

    STATUSES = Choices(
        (DRAFT, _('Draft')),
        (ASSIGNED, _('Assigned')),
        (IN_PROGRESS, _('In Progress')),
        (SUBMITTED, _('Submitted')),
        (FINAL, _('Final')),
        (CANCELLED, _('Cancelled')),
    )

    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Partner'), on_delete=models.CASCADE)
    status = FSMField(verbose_name=_('Status'), max_length=30, choices=STATUSES, default=DRAFT)
    overall_rating = PSEARatingField()

    date_of_field_visit = models.DateField(verbose_name=_('Date of Field Visit'), null=True, blank=True)
    date_assigned = models.DateField(null=True, blank=True)
    date_accepted = models.DateField(null=True, blank=True)
    date_submitted = models.DateField(null=True, blank=True)
    date_finalized = models.DateField(null=True, blank=True)
    date_canceled = models.DateField(null=True, blank=True)

    focal_points = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('UNICEF Focal Points'))

    def calculate_risk(self):
        answers = self.pseaanswer_set
        low = answers.filter(risk=PSEA.LOW).count()
        medium = answers.filter(risk=PSEA.MEDIUM).count()
        high = answers.filter(risk=PSEA.HIGH).count()
        risk_value = 3 * low + 2 * medium + high
        if risk_value <= 11:
            return PSEA.HIGH
        elif 12 <= risk_value < 20:
            return PSEA.MEDIUM
        else:
            return PSEA.LOW

    class Meta:
        verbose_name = _('PSEA')
        verbose_name_plural = _('PSEAs')

    def __str__(self):
        return f'{self.partner} - [{self.status}]'


class PSEAAnswer(TimeStampedModel):
    psea = models.ForeignKey(PSEA, verbose_name=_('PSEA'), on_delete=models.CASCADE)
    indicator = models.ForeignKey(PSEAIndicator, verbose_name=_('Indicator'), on_delete=models.CASCADE)
    evidences = models.ManyToManyField(PSEAEvidence, verbose_name=_('Evidences'))
    rating = PSEARatingField()
    other = models.TextField(verbose_name=_('Other Description'), blank=True, null=True)
    comments = models.TextField(verbose_name=_('Comments'), blank=True, null=True)
    attachments = CodedGenericRelation(Attachment, verbose_name=_('Attachments'), code='psea', blank=True)

    class Meta:
        verbose_name = _('PSEA Answer')
        verbose_name_plural = _('PSEA Answers')

    def __str__(self):
        return f'{self.psea} - [{self.rating}]'
