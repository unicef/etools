from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.attachments.models import Attachment
from etools.applications.audit.purchase_order.models import AuditorFirm, AuditorStaffMember


class Rating(TimeStampedModel):
    label = models.CharField(verbose_name=_("Label"), max_length=50)
    weight = models.IntegerField(verbose_name=_("Weight"))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")

    def __str__(self):
        return f"{self.label}"


class Indicator(TimeStampedModel):
    subject = models.TextField(verbose_name=_('Subject'))
    content = models.TextField(verbose_name=_('Content'))
    ratings = models.ManyToManyField(Rating, verbose_name=_("Rating"))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Indicator')
        verbose_name_plural = _('Indicators')

    def __str__(self):
        return f'{self.subject}'


class Evidence(TimeStampedModel):
    indicators = models.ManyToManyField(
        Indicator,
        verbose_name=_('Indicators'),
    )
    label = models.TextField(verbose_name=_("Label"))
    requires_description = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Evidence')
        verbose_name_plural = _('Evidence')

    def __str__(self):
        return f'{self.label}'


class Engagement(TimeStampedModel):
    partner = models.ForeignKey(
        'partners.PartnerOrganization',
        verbose_name=_('Partner'),
        on_delete=models.CASCADE,
        related_name="psea_engagement",
    )
    overall_rating = models.IntegerField(null=True, blank=True)
    date_of_field_visit = models.DateField(
        verbose_name=_('Date of Field Visit'),
        null=True,
        blank=True,
    )
    focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        verbose_name=_('UNICEF Focal Points'),
    )

    class Meta:
        verbose_name = _('Engagement')
        verbose_name_plural = _('Engagements')
        ordering = ("-date_of_field_visit",)

    def __str__(self):
        return f'{self.partner} [{self.status()}]'

    def status(self):
        return EngagementStatus.objects.filter(engagement=self).first()

    def assessment(self):
        result = Answer.objects.filter(engagement=self).aggregate(
            assessment=Sum("rating__weight")
        )
        if result:
            return result["assessment"]
        return None


class EngagementStatus(TimeStampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_ASSIGNED = 'assigned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_FINAL = 'final'
    STATUS_CANCELLED = 'cancelled'

    STATUSE_CHOICES = Choices(
        (STATUS_DRAFT, _('Draft')),
        (STATUS_ASSIGNED, _('Assigned')),
        (STATUS_IN_PROGRESS, _('In Progress')),
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_FINAL, _('Final')),
        (STATUS_CANCELLED, _('Cancelled')),
    )

    engagement = models.ForeignKey(
        Engagement,
        verbose_name=_("Engagement"),
        on_delete=models.CASCADE,
    )
    status = FSMField(
        verbose_name=_('Status'),
        max_length=30,
        choices=STATUSE_CHOICES,
        default=STATUS_DRAFT,
    )

    class Meta:
        verbose_name = _("Engagement Status")
        verbose_name_plural = _("Engagement Statuses")
        ordering = ("-created",)

    def __str__(self):
        return self.get_status_display()


class Answer(TimeStampedModel):
    engagement = models.ForeignKey(
        Engagement,
        verbose_name=_('Engagement'),
        on_delete=models.CASCADE,
    )
    indicator = models.ForeignKey(
        Indicator,
        verbose_name=_('Indicator'),
        on_delete=models.CASCADE,
    )
    rating = models.ForeignKey(
        Rating,
        verbose_name=_("Rating"),
        on_delete=models.CASCADE,
    )
    comments = models.TextField(
        verbose_name=_('Comments'),
        blank=True,
        null=True,
    )
    attachments = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attachments'),
        code='psea',
        blank=True,
    )

    class Meta:
        verbose_name = _('Answer')
        verbose_name_plural = _('Answers')

    def __str__(self):
        return f'{self.engagement} [{self.rating}]'


class AnswerEvidence(TimeStampedModel):
    answer = models.ForeignKey(
        Answer,
        verbose_name=_("Answer"),
        on_delete=models.CASCADE,
    )
    evidence = models.ForeignKey(
        Evidence,
        verbose_name=_("Evidence"),
        on_delete=models.CASCADE,
    )
    description = models.TextField(
        verbose_name=_('Description'),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Answer Evidence")
        verbose_name_plural = _("Answer Evidences")

    def __str__(self):
        return f"{self.evidence}"


class Assessor(TimeStampedModel):
    TYPE_SSA = "ssa"
    TYPE_UNICEF = "unicef"
    TYPE_VENDOR = "vendor"

    TYPE_CHOICES = Choices(
        (TYPE_SSA, _("SSA")),
        (TYPE_UNICEF, _("UNICEF")),
        (TYPE_VENDOR, _("Vendor")),
    )

    engagement = models.ForeignKey(
        Engagement,
        verbose_name=_("Engagement"),
        on_delete=models.CASCADE,
    )
    assessor_type = models.CharField(
        verbose_name=_("Type"),
        max_length=30,
        choices=TYPE_CHOICES,
    )
    unicef_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("UNICEF User"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    auditor_firm = models.ForeignKey(
        AuditorFirm,
        verbose_name=_('Auditor'),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    order_number = models.CharField(
        verbose_name=_('Order Number'),
        null=True,
        blank=True,
        unique=True,
        max_length=30
    )
    audit_firm_staff = models.ManyToManyField(
        AuditorStaffMember,
        verbose_name=_("Auditor Staff"),
    )

    class Meta:
        verbose_name = "Assessor"
        verbose_name_plural = "Assessors"

    def __str__(self):
        if self.assessor_type == Assessor.TYPE_VENDOR:
            return f"{self.auditor_firm}"
        return f"{self.unicef_user}"
