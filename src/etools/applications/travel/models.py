from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_locations.models import Location

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.travel.validation import itinerary_illegal_transition
from etools.applications.users.models import WorkspaceCounter


def generate_reference_number():
    with transaction.atomic():
        numeric_part = connection.tenant.counters.get_next_value(
            WorkspaceCounter.TRAVEL_REFERENCE
        )
    year = timezone.now().year
    return '{}/{}'.format(year, numeric_part)


class Itinerary(TimeStampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMISSION_REVIEW = 'submission'
    STATUS_SUBMITTED = 'submitted'
    STATUS_REJECTED = 'rejected'
    STATUS_APPROVED = 'approved'
    STATUS_REVIEW = 'review'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = Choices(
        (STATUS_DRAFT, _('Draft')),
        (STATUS_SUBMISSION_REVIEW, _('Submission Review')),
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REVIEW, _('REVIEW')),
        (STATUS_COMPLETED, _('Completed')),
        (STATUS_CANCELLED, _('Cancelled')),
    )

    AUTO_TRANSITIONS = {}
    TRANSITION_SIDE_EFFECTS = {}

    reference_number = models.CharField(
        max_length=15,
        verbose_name=_("Reference Number"),
        unique=True,
        default=generate_reference_number,
    )
    status = FSMField(
        verbose_name=_('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Supervisor'),
        on_delete=models.CASCADE,
        related_name="supervised_itineraries",
    )
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )
    start_date = models.DateField(
        verbose_name=_('Start Date'),
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name=_('End Date'),
        null=True,
        blank=True,
    )
    traveller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Traveller"),
        on_delete=models.CASCADE,
        related_name="itineraries",
    )
    attachments = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attachments'),
        code='travel_docs',
        blank=True,
    )

    class Meta:
        verbose_name = _('Itinerary')
        verbose_name_plural = _('Itineraries')
        ordering = ("-start_date",)

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def __str__(self):
        return f'{self.traveller} [{self.get_status_display()}] {self.reference_number}'

    def get_object_url(self, **kwargs):
        return build_frontend_url(
            'travel',
            'itinerary',
            'detail',
            self.pk,
            **kwargs,
        )

    def get_rejected_comment(self):
        rejected_qs = self.status_history.filter(
            status=Itinerary.STATUS_REJECTED,
        )
        if rejected_qs.exists():
            return rejected_qs.first().comment
        return None

    def get_mail_context(self, user):
        context = {
            "url": self.get_object_url(user=user),
            "itinerary": self
        }
        if self.status == self.STATUS_REJECTED:
            context["rejected_comment"] = self.get_rejected_comment()
        return context

    @transition(
        field=status,
        source=[STATUS_DRAFT],
        target=[STATUS_SUBMISSION_REVIEW],
    )
    def transition_to_submission_review(self):
        """Itinerary moves to submission review status"""

    @transition(
        field=status,
        source=[STATUS_SUBMISSION_REVIEW],
        target=[STATUS_SUBMITTED],
    )
    def transition_to_submitted(self):
        """Itinerary moves to submitted status"""

    @transition(
        field=status,
        source=[STATUS_SUBMITTED, STATUS_SUBMISSION_REVIEW],
        target=[STATUS_APPROVED],
    )
    def transition_to_approved(self):
        """Itinerary moves to approved status"""

    @transition(
        field=status,
        source=[STATUS_APPROVED],
        target=[STATUS_REVIEW],
    )
    def transition_to_review(self):
        """Itinerary moves to review status"""

    @transition(
        field=status,
        source=[STATUS_APPROVED, STATUS_REVIEW],
        target=[STATUS_COMPLETED],
    )
    def transition_to_completed(self):
        """Itinerary moves to completed status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_REJECTED,
            STATUS_APPROVED,
        ],
        target=[STATUS_CANCELLED],
    )
    def transition_to_cancelled(self):
        """Itinerary moves to cancelled status"""

    @transition(
        field=status,
        source=[STATUS_REJECTED, STATUS_SUBMISSION_REVIEW],
        target=[STATUS_DRAFT],
    )
    def transition_to_draft(self):
        """Itinerary moves to draft status"""

    # illegal transitions
    @transition(
        field=status,
        source=[
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_DRAFT],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_draft_invalid(self):
        """Not allowed to move to draft status"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_SUBMISSION_REVIEW],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_submission_review_invalid(self):
        """Not allowed to move to submission review status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_SUBMITTED],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_submitted_invalid(self):
        """Not allowed to move to submitted status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_APPROVED],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_approved_invalid(self):
        """Not allowed to move to approved status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_REVIEW],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_review_invalid(self):
        """Not allowed to move to review status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_COMPLETED],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_completed_invalid(self):
        """Not allowed to move to completed status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_REJECTED],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_rejected_invalid(self):
        """Not allowed to move to rejected status"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMITTED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
        ],
        target=[STATUS_CANCELLED],
        conditions=[itinerary_illegal_transition],
    )
    def transition_to_cancelled_invalid(self):
        """Allowed to move to cancelled status"""


class ItineraryItem(TimeStampedModel):
    itinerary = models.ForeignKey(
        Itinerary,
        verbose_name=_("Itinerary"),
        on_delete=models.CASCADE,
        related_name="items",
    )
    start_date = models.DateField(
        verbose_name=_('Start Date'),
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name=_('End Date'),
        null=True,
        blank=True,
    )
    travel_method = models.CharField(
        max_length=150,
        verbose_name=_("Travel Method"),
        blank=True
    )
    destination = models.CharField(
        max_length=150,
        verbose_name=_("Destination"),
        blank=True,
    )

    class Meta:
        verbose_name = "Itinerary Item"
        verbose_name_plural = "Itinerary Items"

    def __str__(self):
        return f"{self.itinerary} Item {self.travel_method}"


class ItineraryStatusHistory(TimeStampedModel):
    itinerary = models.ForeignKey(
        Itinerary,
        verbose_name=_("Itinerary"),
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(
        max_length=30,
        choices=Itinerary.STATUS_CHOICES,
    )
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Itinerary Status History")
        verbose_name_plural = _("Itinerary Status History")
        ordering = ("-created",)

    def __str__(self):
        return f"{self.get_status_display()} [{self.created}]"


class Activity(TimeStampedModel):
    TYPE_PROGRAMME_MONITORING = 'Programmatic Visit'
    TYPE_SPOT_CHECK = 'Spot Check'
    TYPE_ADVOCACY = 'Advocacy'
    TYPE_TECHNICAL_SUPPORT = 'Technical Support'
    TYPE_MEETING = 'Meeting'
    TYPE_STAFF_DEVELOPMENT = 'Staff Development'
    TYPE_STAFF_ENTITLEMENT = 'Staff Entitlement'
    TYPE_CHOICES = (
        (TYPE_PROGRAMME_MONITORING, 'Programmatic Visit'),
        (TYPE_SPOT_CHECK, 'Spot Check'),
        (TYPE_ADVOCACY, 'Advocacy'),
        (TYPE_TECHNICAL_SUPPORT, 'Technical Support'),
        (TYPE_MEETING, 'Meeting'),
        (TYPE_STAFF_DEVELOPMENT, 'Staff Development'),
        (TYPE_STAFF_ENTITLEMENT, 'Staff Entitlement'),
    )

    itinerary = models.ForeignKey(
        Itinerary,
        verbose_name=_("Itinerary"),
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity_date = models.DateField(
        verbose_name=_("Activity Date")
    )
    activity_type = models.CharField(
        max_length=64,
        verbose_name=_("Activity Type"),
        choices=TYPE_CHOICES,
        default=TYPE_PROGRAMME_MONITORING,
        blank=True,
    )

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.activity_date}"


class Involved(TimeStampedModel):
    TYPE_SECTION = "section"
    TYPE_RESULT = "result"
    TYPE_INTERVENTION = "intervention"
    TYPE_PARTNER = "partner"
    TYPE_ACTION_POINT = "action_point"
    TYPE_MONITORING = "monitoring"
    TYPE_CHOICES = [
        (TYPE_SECTION, _("Section")),
        (TYPE_RESULT, _("Result")),
        (TYPE_INTERVENTION, _("Intervention")),
        (TYPE_PARTNER, _("Partner")),
        (TYPE_ACTION_POINT, _("Action Point")),
        (TYPE_MONITORING, _("FM Monitoring Activity")),
    ]

    activity = models.OneToOneField(
        Activity,
        verbose_name=_("Activity"),
        on_delete=models.CASCADE,
        related_name="involved",
    )
    involved_type = models.CharField(
        verbose_name=_("Type"),
        max_length=30,
        choices=TYPE_CHOICES,
    )
    related_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    related_id = models.PositiveIntegerField()
    related_object = GenericForeignKey('related_type', 'related_id')
    location = models.ForeignKey(
        Location,
        verbose_name=_("Location"),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Involved")
        verbose_name_plural = _("Involved")

    def __str__(self):
        return f"{self.get_involved_type_display()} {self.related_object}"


class ActivityActionPointManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(travel__isnull=False)


class ActivityActionPoint(ActionPoint):
    """This proxy class is for easier permissions assigning."""
    objects = ActivityActionPointManager()

    class Meta(ActionPoint.Meta):
        verbose_name = _('Travel Activity Action Point')
        verbose_name_plural = _('Travel Activity Action Points')
        proxy = True

    def get_mail_context(self, user=None):
        context = super().get_mail_context(user=user)
        if self.travel:
            context['travel'] = self.travel.get_mail_context(
                user=user,
            )
        return context


class Report(TimeStampedModel):
    itinerary = models.OneToOneField(
        Itinerary,
        verbose_name=_("Itinerary"),
        on_delete=models.CASCADE,
        related_name="report",
    )
    narrative = models.TextField(
        verbose_name=_("Narrative"),
        blank=True,
    )
    attachments = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attachments'),
        code='travel_report_docs',
        blank=True,
    )

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return f"{self.itinerary} Report"
