from django.conf import settings
from django.db import connection, models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.purchase_order.models import AuditorFirm, AuditorStaffMember
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url


class Rating(TimeStampedModel):
    label = models.CharField(verbose_name=_("Label"), max_length=50)
    weight = models.IntegerField(verbose_name=_("Weight"))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")

    def __str__(self):
        return f"{self.label}"


class Evidence(TimeStampedModel):
    label = models.TextField(verbose_name=_("Label"))
    requires_description = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Evidence')
        verbose_name_plural = _('Evidence')

    def __str__(self):
        return f'{self.label}'


class Indicator(TimeStampedModel):
    subject = models.TextField(verbose_name=_('Subject'))
    content = models.TextField(verbose_name=_('Content'))
    ratings = models.ManyToManyField(Rating, verbose_name=_("Rating"))
    evidences = models.ManyToManyField(Evidence, verbose_name=_('Evidences'))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Indicator')
        verbose_name_plural = _('Indicators')

    def __str__(self):
        return f'{self.subject}'


class Assessment(TimeStampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_ASSIGNED = 'assigned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_REJECTED = 'rejected'
    STATUS_FINAL = 'final'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = Choices(
        (STATUS_DRAFT, _('Draft')),
        (STATUS_ASSIGNED, _('Assigned')),
        (STATUS_IN_PROGRESS, _('In Progress')),
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_FINAL, _('Final')),
        (STATUS_CANCELLED, _('Cancelled')),
    )

    AUTO_TRANSITIONS = {
        STATUS_ASSIGNED: [STATUS_IN_PROGRESS],
    }

    reference_number = models.CharField(
        max_length=100,
        verbose_name=_("Reference Number"),
        unique=True,
    )
    partner = models.ForeignKey(
        'partners.PartnerOrganization',
        verbose_name=_('Partner'),
        on_delete=models.CASCADE,
        related_name="psea_assessment",
    )
    overall_rating = models.IntegerField(null=True, blank=True)
    assessment_date = models.DateField(
        verbose_name=_('Assessment Date'),
        null=True,
        blank=True,
    )
    status = FSMField(
        verbose_name=_('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        verbose_name=_('UNICEF Focal Points'),
        related_name="assessor_focal_point",
    )

    class Meta:
        verbose_name = _('Assessment')
        verbose_name_plural = _('Assessments')
        ordering = ("-assessment_date",)

    def get_object_url(self, **kwargs):
        # TODO double check this with frontend developers
        return build_frontend_url('psea', 'assessment', 'detail', self.id, **kwargs)

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def __str__(self):
        return f'{self.partner} [{self.get_status_display()}] {self.reference_number}'

    def rating(self):
        result = Answer.objects.filter(assessment=self).aggregate(
            assessment=Sum("rating__weight")
        )
        if result:
            return result["assessment"]
        return None

    def get_reference_number(self):
        return "{code}/{year}PSEA{num}".format(
            code=connection.tenant.country_short_code,
            year=timezone.now().year,
            num=self.pk,
        )

    def save(self, *args, **kwargs):
        self.overall_rating = self.rating()
        super().save(*args, **kwargs)
        if not self.reference_number:
            self.reference_number = self.get_reference_number()
            self.save()
        last_status = self.status_history.first()
        if not last_status or last_status.status != self.status:
            AssessmentStatusHistory.objects.create(
                assessment=self,
                status=self.status,
            )

    @transition(
        field=status,
        source=[STATUS_DRAFT],
        target=[STATUS_ASSIGNED],
    )
    def transition_to_assigned(self):
        """Assessment moves to assigned status"""
        # TODO needs to focal point user

    @transition(
        field=status,
        source=[STATUS_ASSIGNED],
        target=[STATUS_IN_PROGRESS],
    )
    def transition_to_in_progress(self):
        """Assessment moves to in progress status"""
        # TODO auto

    @transition(
        field=status,
        source=[STATUS_IN_PROGRESS],
        target=[STATUS_SUBMITTED],
    )
    def transition_to_submitted(self):
        """Assessment moves to submitted status"""
        # TODO needs to belongs

    @transition(
        field=status,
        source=[STATUS_SUBMITTED],
        target=[STATUS_FINAL],
    )
    def transition_to_final(self):
        """Assessment moves to final status"""
        # TODO needs to focal point user

    @transition(
        field=status,
        source=[STATUS_SUBMITTED],
        target=[STATUS_IN_PROGRESS],
    )
    def transition_to_rejected(self):
        """Assessment rejected"""
        # TODO needs to focal point user

    @transition(
        field=status,
        source=[STATUS_DRAFT, STATUS_IN_PROGRESS],
        target=[STATUS_CANCELLED],
    )
    def transition_to_cancelled(self):
        """Assessment cancelled"""
        # TODO except from SUBMITED/FINAL


class AssessmentStatusHistory(TimeStampedModel):
    assessment = models.ForeignKey(
        Assessment,
        verbose_name=_("Assessment"),
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(
        max_length=30,
        choices=Assessment.STATUS_CHOICES,
    )
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Assessment Status History")
        verbose_name_plural = _("Assessment Status History")
        ordering = ("-created",)

    def __str__(self):
        return f"{self.get_status_display()} [{self.created}]"


class AssessmentActionPointManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(psea_assessment__isnull=False)


class AssessmentActionPoint(ActionPoint):
    """This proxy class is for easier permissions assigning."""
    objects = AssessmentActionPointManager()

    class Meta(ActionPoint.Meta):
        verbose_name = _('PSEA Assessment Action Point')
        verbose_name_plural = _('PSEA Assessment Action Points')
        proxy = True

    def get_mail_context(self, user=None):
        context = super().get_mail_context(user=user)
        if self.psea_assessment:
            context['psea_assessment'] = self.psea_assessment.get_mail_context(
                user=user,
            )
        return context


class Answer(TimeStampedModel):
    assessment = models.ForeignKey(
        Assessment,
        verbose_name=_('Assessment'),
        on_delete=models.CASCADE,
        related_name="answers",
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
        code='psea_answer',
        blank=True,
    )

    class Meta:
        verbose_name = _('Answer')
        verbose_name_plural = _('Answers')
        unique_together = [["assessment", "indicator"]]

    def __str__(self):
        return f'{self.assessment} [{self.rating}]'


class AnswerEvidence(TimeStampedModel):
    answer = models.ForeignKey(
        Answer,
        verbose_name=_("Answer"),
        on_delete=models.CASCADE,
        related_name="evidences",
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
    TYPE_EXTERNAL = "external"
    TYPE_UNICEF = "staff"
    TYPE_VENDOR = "firm"

    TYPE_CHOICES = Choices(
        (TYPE_EXTERNAL, _("External Individual")),
        (TYPE_UNICEF, _("UNICEF Staff")),
        (TYPE_VENDOR, _("Assessing Firm")),
    )

    assessment = models.OneToOneField(
        Assessment,
        verbose_name=_("Assessment"),
        on_delete=models.CASCADE,
        related_name="assessor",
    )
    assessor_type = models.CharField(
        verbose_name=_("Type"),
        max_length=30,
        choices=TYPE_CHOICES,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
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
        blank=True,
        max_length=30
    )
    auditor_firm_staff = models.ManyToManyField(
        AuditorStaffMember,
        blank=True,
        verbose_name=_("Auditor Staff"),
    )

    class Meta:
        verbose_name = "Assessor"
        verbose_name_plural = "Assessors"

    def __str__(self):
        if self.assessor_type == Assessor.TYPE_VENDOR:
            return f"{self.auditor_firm}"
        return f"{self.user}"
