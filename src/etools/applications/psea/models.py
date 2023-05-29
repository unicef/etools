from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.purchase_order.models import AuditorFirm
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.psea.validation import (
    assessment_assigned,
    assessment_assigned_reassessment,
    assessment_final,
    assessment_focal_point_user,
    assessment_illegal_transition,
    assessment_rejected,
    assessment_submitted,
    assessment_user_belongs,
)


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


class Indicator(OrderedModel, TimeStampedModel):
    subject = models.TextField(verbose_name=_('Subject'))
    content = models.TextField(verbose_name=_('Content'))
    ratings = models.ManyToManyField(Rating, verbose_name=_("Rating"))
    rating_instructions = models.TextField(
        verbose_name=_("Rating Instructions"),
        blank=True,
    )
    evidences = models.ManyToManyField(Evidence, verbose_name=_('Evidences'))
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)
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
    TRANSITION_SIDE_EFFECTS = {
        STATUS_ASSIGNED: [assessment_assigned, assessment_assigned_reassessment],
        STATUS_SUBMITTED: [assessment_submitted],
        STATUS_REJECTED: [assessment_rejected],
        STATUS_FINAL: [assessment_final],
    }

    LOW_RATING = "Low"
    MODERATE_RATING = "Moderate"
    HIGH_RATING = "High"
    RATING = {
        LOW_RATING: LOW_RATING,
        MODERATE_RATING: MODERATE_RATING,
        HIGH_RATING: HIGH_RATING
    }

    UNICEF_2020 = 'unicef_2020'
    UN_COMMON_OTHER = 'un_common_other'
    UN_COMMON_UNICEF = 'un_common_unicef'

    ASSESSMENT_TYPES = (
        (UNICEF_2020, _("UNICEF Assessment 2020")),
        (UN_COMMON_OTHER, _("UN Common Assessment- Other UN")),
        (UN_COMMON_UNICEF, _("UN Common Assessment- UNICEF")),
    )

    DECENTRALIZED = 'decentralized'
    SEA_ALLEGATION = 'sea_allegation'
    GLOBAL_POLICY_IMPLEMENTED = 'global_policy_implemented'
    HIGH_RISK_CONTEXT = 'high_risk_context'

    INGO_REASONS = (
        (DECENTRALIZED, _("Decentralization of INGO")),
        (SEA_ALLEGATION, _("SEA allegation")),
        (GLOBAL_POLICY_IMPLEMENTED, _("Global policy not being implemented at country-level")),
        (HIGH_RISK_CONTEXT, _("High risk context")),
    )

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
    assessment_type = models.CharField(max_length=16, choices=ASSESSMENT_TYPES, default=UNICEF_2020)
    assessment_ingo_reason = models.CharField(max_length=32, choices=INGO_REASONS, blank=True, null=True)
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
        related_name="pse_assessment_focal_point",
    )
    nfr_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('NFR Attachment'),
        code='psea_nfr_attachment',
        blank=True,
    )

    class Meta:
        verbose_name = _('Assessment')
        verbose_name_plural = _('Assessments')
        ordering = ("-assessment_date",)

    def get_object_url(self, **kwargs):
        return build_frontend_url('psea', 'assessments', self.id, 'details', **kwargs)

    def get_rejected_comment(self):
        rejected_qs = self.status_history.filter(
            status=Assessment.STATUS_REJECTED,
        )
        if rejected_qs.exists():
            return rejected_qs.first().comment
        return None

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def __str__(self):
        return f'{self.partner} [{self.get_status_display()}] {self.reference_number}'

    def answers_complete(self):
        """Check if all answers have been provided"""
        indicators_qs = Indicator.objects.filter(active=True)
        answers_qs = self.answers.filter(
            indicator__pk__in=indicators_qs.values_list("pk", flat=True),
        )
        if indicators_qs.count() == answers_qs.count():
            return True
        return False

    @property
    def overall_rating_display(self):
        if not self.overall_rating:
            display = ""
        elif self.overall_rating <= 8:
            display = Assessment.HIGH_RATING
        elif 8 < self.overall_rating <= 14:
            display = Assessment.MODERATE_RATING
        elif self.overall_rating >= 15:
            display = Assessment.LOW_RATING
        return display

    def get_assessor_recipients(self):
        return self.assessor.get_recipients()

    def get_focal_recipients(self):
        return [u.email for u in self.focal_points.all()]

    def get_all_recipients(self):
        return self.get_assessor_recipients() + self.get_focal_recipients()

    def rating(self):
        if self.answers_complete():
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

    def update_rating(self):
        self.overall_rating = self.rating()
        self.save()

    def user_is_assessor(self, user):
        assessor_qs = Assessor.objects.filter(assessment=self)
        if assessor_qs.filter(user=user).exists():
            return True
        for assessor in assessor_qs.all():
            if assessor.auditor_firm_staff.filter(id=user.id).exists():
                return True
        return False

    def user_is_external(self, user):
        assessor_qs = Assessor.objects.filter(
            assessment=self,
            assessor_type=Assessor.TYPE_EXTERNAL,
        )
        if assessor_qs.filter(user=user).exists():
            return True
        return False

    def user_belongs(self, user):
        if self.pk and user in self.focal_points.all():
            return True
        return self.user_is_assessor(user)

    def get_mail_context(self, user):
        nfr_attachment = self.nfr_attachment.first()
        if nfr_attachment:
            nfr_attachment = settings.HOST + reverse('attachments:file', kwargs={'pk': nfr_attachment.pk})
        context = {
            "partner_name": self.partner.name,
            "partner_vendor_number": self.partner.vendor_number,
            "url": self.get_object_url(user=user),
            'reference_number': self.get_reference_number(),
            "overall_rating": self.overall_rating_display,
            "assessment_date": str(self.assessment_date),
            "assessment_type": self.get_assessment_type_display(),
            "assessment_ingo_reason": self.get_assessment_ingo_reason_display(),
            "assessor": str(getattr(self, 'assessor', '')),
            "focal_points": ", ".join(f"{fp.get_full_name()} ({fp.email})" for fp in self.focal_points.all()),
            "nfr_attachment": nfr_attachment
        }
        if self.status == self.STATUS_REJECTED:
            context["rejected_comment"] = self.get_rejected_comment()
        return context

    def save(self, *args, **kwargs):
        self.overall_rating = self.rating()
        super().save(*args, **kwargs)
        if not self.reference_number:
            self.reference_number = self.get_reference_number()
            self.save()

    @transition(
        field=status,
        source=[STATUS_DRAFT],
        target=[STATUS_ASSIGNED],
        permission=assessment_focal_point_user,
    )
    def transition_to_assigned(self):
        """Assessment moves to assigned status"""

    @transition(
        field=status,
        source=[STATUS_ASSIGNED],
        target=[STATUS_IN_PROGRESS],
    )
    def transition_to_in_progress(self):
        """Assessment moves to in progress status"""

    @transition(
        field=status,
        source=[STATUS_IN_PROGRESS, STATUS_REJECTED],
        target=[STATUS_SUBMITTED],
        permission=assessment_user_belongs,
    )
    def transition_to_submitted(self):
        """Assessment moves to submitted status"""

    @transition(
        field=status,
        source=[STATUS_SUBMITTED],
        target=[STATUS_FINAL],
        permission=assessment_focal_point_user,
    )
    def transition_to_final(self):
        """Assessment moves to final status"""

    @transition(
        field=status,
        source=[STATUS_SUBMITTED],
        target=[STATUS_REJECTED],
        permission=assessment_focal_point_user,
    )
    def transition_to_rejected(self):
        """Assessment rejected"""

    @transition(
        field=status,
        source=[STATUS_DRAFT, STATUS_IN_PROGRESS],
        target=[STATUS_CANCELLED],
        permission=assessment_focal_point_user,
    )
    def transition_to_cancelled(self):
        """Assessment cancelled"""

    @transition(
        field=status,
        source=[
            STATUS_ASSIGNED,
            STATUS_IN_PROGRESS,
            STATUS_SUBMITTED,
            STATUS_REJECTED,
            STATUS_FINAL,
            STATUS_CANCELLED,
        ],
        target=[STATUS_DRAFT],
        conditions=[assessment_illegal_transition],
    )
    def transition_to_draft_invalid(self):
        """Not allowed to move back to draft status"""

    @transition(
        field=status,
        source=[
            STATUS_IN_PROGRESS,
            STATUS_SUBMITTED,
            STATUS_REJECTED,
            STATUS_FINAL,
            STATUS_CANCELLED,
        ],
        target=[STATUS_ASSIGNED],
        conditions=[assessment_illegal_transition],
    )
    def transition_to_assigned_invalid(self):
        """Not allowed to move back to assigned status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_ASSIGNED,
            STATUS_IN_PROGRESS,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_FINAL],
        conditions=[assessment_illegal_transition],
    )
    def transition_to_final_invalid(self):
        """Not allowed to move to final status, except from submitted"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_ASSIGNED,
            STATUS_IN_PROGRESS,
            STATUS_FINAL,
            STATUS_CANCELLED,
        ],
        target=[STATUS_REJECTED],
        conditions=[assessment_illegal_transition],
    )
    def transition_to_rejected_invalid(self):
        """Not allowed to move to rejected status, except from submitted"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMITTED,
            STATUS_FINAL,
        ],
        target=[STATUS_CANCELLED],
        conditions=[assessment_illegal_transition],
    )
    def transition_to_cancelled_invalid(self):
        """Allowed to move to cancelled status, except from submitted/final"""

    def get_related_third_party_users(self):
        return get_user_model().objects.filter(
            models.Q(pk=self.assessor.user_id) |
            models.Q(pk__in=self.assessor.auditor_firm_staff.values_list('id', flat=True))
        )


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.assessment.update_rating()

    def get_related_third_party_users(self):
        return self.assessment.get_related_third_party_users()


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
        settings.AUTH_USER_MODEL,
        blank=True,
        verbose_name=_("Auditor Staff"),
        related_name='+'
    )

    class Meta:
        verbose_name = "Assessor"
        verbose_name_plural = "Assessors"

    def __str__(self):
        if self.assessor_type == Assessor.TYPE_VENDOR:
            return f"{self.auditor_firm}"
        return f"{self.user}"

    def get_recipients(self):
        if self.assessor_type in [self.TYPE_EXTERNAL, self.TYPE_UNICEF]:
            return [self.user.email]
        else:
            return [s.email for s in self.auditor_firm_staff.all()]
